import os, uuid
from dataclasses import asdict
from backend.config import WORKDIR
from backend.pipeline import transcribe as T
from backend.config import BOOST, MUSIC as MUSIC_CFG
from backend import settings as settings_mod
from backend.pipeline import (audio_clean, align, subtitles, montage, detect, waveform,
                              sfx_plan, caption, keywords, director, audio_meta)
from backend.pipeline import tunnel, publish_ig

# Exposé pour le mode debug / tests (jamais utilisé en logique métier)
_LAST_MUSIC_DEBUG = None

def _analyze(clean_path):
    """Transcrit + détecte + pics. Brique commune à load et cut."""
    words, duration = T.transcribe(clean_path)
    transcript = " ".join(w.text for w in words)
    return {
        "clean_path": clean_path,
        "duration": duration,
        "transcript": transcript,
        "words": [asdict(w) for w in words],
        "detect": detect.detect(words),
        "peaks": waveform.peaks(clean_path),
        "caption": caption.generate_caption(transcript),
    }

def load_audio(audio_path):
    """Nettoie les silences puis transcrit + détecte (🟡 reprises / 🔴 mots peu sûrs)."""
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Fichier introuvable (déplacé ou renommé ?) : {audio_path}")
    job = os.path.join(WORKDIR, uuid.uuid4().hex)
    os.makedirs(job, exist_ok=True)
    clean = os.path.join(job, "clean.mp3")
    audio_clean.remove_silences(audio_path, clean)
    res = _analyze(clean)
    res["job"] = job
    return res

def cut(clean_path, ranges):
    """Retire des plages [(start,end)] de l'audio nettoyé, re-transcrit + re-détecte."""
    job = os.path.dirname(clean_path)
    new = os.path.join(job, f"clean_{uuid.uuid4().hex}.mp3")
    audio_clean.cut_audio(clean_path, new, [tuple(r) for r in ranges])
    res = _analyze(new)
    res["job"] = job
    return res

def make_caption(text):
    return caption.generate_caption(text)

def get_settings():
    s = settings_mod.load()
    return {"ig_user_id": s.get("ig_user_id", ""), "has_token": bool(s.get("ig_token"))}

def save_settings(ig_token, ig_user_id):
    settings_mod.save({"ig_token": ig_token, "ig_user_id": ig_user_id})
    return get_settings()

def publish_instagram(video_path, caption_text):
    s = settings_mod.load()
    token, uid = s.get("ig_token"), s.get("ig_user_id")
    if not token or not uid:
        raise RuntimeError("Configure ton token et ton IG ID dans Réglages d'abord.")
    media_id = publish_ig.publish_reel(video_path, caption_text, token, uid, tunnel.public_url)
    return {"id": media_id}

def _music_dominance_autofix(debug, *, render_callable, current_gain,
                              voice_path, mix_path, voice_active):
    """Mesure la dominance voix sur le mix.

    - Si OK : ne fait rien.
    - Si trop faible : baisse la musique de auto_fix_step_dB, RE-RENDU UNE FOIS,
      re-mesure. Log un warning explicatif.
    - Si toujours trop faible après auto-fix : log un warning, mais GARDE la vidéo.

    JAMAIS bloquant : retourne (True, debug) dans TOUS les cas (même si une
    erreur interne survient pendant la mesure).
    """
    try:
        # Métrique perceptive : RMS(voix isolée) - RMS(musique isolée traitée).
        # Résiste au biais "voix dans mix" qui faisait tendre la mesure vers 0.
        dom = audio_meta.measure_dominance_perceptive(
            mix_path, voice_path, voice_active)
        debug["voice_dominance_dB"] = dom

        if dom >= MUSIC_CFG["voice_dominance_min_dB"]:
            return True, debug   # tout va bien

        # Auto-fix : baisse de auto_fix_step_dB et re-rendu unique
        new_gain = current_gain + MUSIC_CFG["auto_fix_step_dB"]
        render_callable(new_gain)
        debug["auto_fix_applied"] = True

        # Re-mesure post-auto-fix
        dom2 = audio_meta.measure_dominance_perceptive(
            mix_path, voice_path, voice_active)
        debug["voice_dominance_dB"] = dom2

        if dom2 >= MUSIC_CFG["voice_dominance_min_dB"]:
            debug["warnings"].append(
                f"voice dominance was {dom:.1f} dB, auto-reduced music by "
                f"{abs(MUSIC_CFG['auto_fix_step_dB']):.0f} dB (now {dom2:.1f} dB)"
            )
        else:
            debug["warnings"].append(
                f"voice dominance still below {MUSIC_CFG['voice_dominance_min_dB']} dB "
                f"after auto-fix (value={dom2:.1f} dB) — video kept"
            )
        return True, debug
    except Exception as e:    # garde-fou absolu : jamais bloquant
        debug["warnings"].append(f"autofix internal error (kept video): {e}")
        return True, debug


def make_video(clean_path, text, out_path, style="karaoke_yellow", boost=False):
    """Pipeline officiel :
       transcribe -> align -> detect_events -> sentence_ranges (+ boost cuts)
       -> Director.build_plan -> renderers exécutifs (subtitles + montage).
    """
    words, duration = T.transcribe(clean_path)
    tokens, n_sent = align.tokenize(text)
    align.align(tokens, words)

    # 1) Détection événements normalisés (source unique)
    events = keywords.detect_events(tokens)

    # 2) Plages de clips (et redécoupage hook si Boost)
    ranges = montage.sentence_ranges(tokens, n_sent, duration)
    if boost:
        ranges = montage.apply_boost_cuts(ranges, BOOST["hook_dur"], BOOST["hook_cut"])

    # 3) SFX events (rester sur le pipeline expert existant, lui aussi event-driven)
    sfx_events = None
    if boost:
        sw = [T.Word(t["disp"], t["start"], t["end"], 1.0) for t in tokens]
        phrases = []
        for si in range(n_sent):
            ts = [t for t in tokens if t["sent"] == si]
            if ts:
                phrases.append((ts[0]["start"], ts[-1]["end"]))
        cuts = [r[0] for r in ranges if r[0] > 0.01]
        sfx_events = sfx_plan.generate_sfx(sw, phrases, cuts, duration, BOOST["hook_dur"])

    # 4) Director -> plan unique (subtitles + motion + transitions)
    plan = director.build_plan(events, tokens, n_sent, ranges, duration)

    # 5) Renderers exécutifs
    job = os.path.dirname(clean_path)
    ass = os.path.join(job, "subs.ass")
    st_mode = subtitles.STYLES.get(style, subtitles.STYLES[subtitles.DEFAULT_STYLE])["mode"]
    if st_mode == "premium":
        subtitles.render_plan_subs(plan["subtitles"], ass, style=style)
    else:
        subtitles.build_ass(tokens, n_sent, ass, style=style)

    # Mastering : appliqué par défaut (target_lufs lu dans config) sauf si
    # explicitement désactivé via MUSIC_CFG["master_lufs_target"]=None.
    master_lufs = MUSIC_CFG.get("master_lufs_target")

    montage.render(clean_path, ass, ranges, out_path,
                   boost=boost, sfx_events=sfx_events, plan=plan,
                   master_lufs=master_lufs)

    # 6) Mesures musique post-rendu + auto-fix non bloquant + quality score.
    #    Tout est protégé pour ne JAMAIS interrompre la sortie de la vidéo.
    global _LAST_MUSIC_DEBUG
    _LAST_MUSIC_DEBUG = None
    music = plan.get("music")
    if music and music.get("beds"):
        debug = music["debug"]
        bed = music["beds"][0]
        try:
            debug["lufs_voice"] = audio_meta.lufs_of(clean_path)
            debug["lufs_music_source"] = audio_meta.lufs_of(bed["track"])
            debug["lufs_final_actual"] = audio_meta.lufs_of(out_path)
            # lufs estimé après application de base_gain (pour traçabilité)
            debug["lufs_music_at_base"] = round(
                debug["lufs_music_source"] + bed["base_gain_dB"], 2)
        except Exception as e:
            debug.setdefault("warnings", []).append(
                f"lufs measurement skipped (kept video): {e}")

        voice_active = [(e["start"], e["end"])
                        for e in director._voice_active_events(tokens)]

        def _re_render(new_gain):
            bed["base_gain_dB"] = new_gain
            # depth_dB inchangé : on baisse seulement la base, pas le ducking.
            # IMPORTANT : on garde master_lufs sinon l'auto-fix écraserait
            # le rendu masterisé par un rendu non masterisé.
            montage.render(clean_path, ass, ranges, out_path,
                           boost=boost, sfx_events=sfx_events, plan=plan,
                           master_lufs=master_lufs)
            # Met à jour les LUFS post-render
            try:
                debug["lufs_final_actual"] = audio_meta.lufs_of(out_path)
                debug["lufs_music_at_base"] = round(
                    debug["lufs_music_source"] + new_gain, 2)
            except Exception:
                pass

        # Mesure dominance sur le mix PRÉ-mastering (sinon le gain mastering
        # appliqué uniformément fausse la comparaison voix isolée vs musique
        # isolée). Si pas de mastering, premaster_path est None et on retombe
        # sur out_path directement.
        mix_for_dominance = (getattr(montage.render, "_premaster_path", None)
                              or out_path)
        _music_dominance_autofix(
            debug, render_callable=_re_render,
            current_gain=bed["base_gain_dB"],
            voice_path=clean_path, mix_path=mix_for_dominance,
            voice_active=voice_active,
        )
        debug["music_quality_score"] = director._compute_quality_score(debug)

        # --- Mastering debug enrichi (V1 : gain statique uniforme) ---
        if master_lufs is not None:
            try:
                debug["target_lufs"] = master_lufs
                debug["lufs_pre_master"] = getattr(montage.render,
                                                   "_last_input_lufs", None)
                debug["master_gain_dB"] = getattr(montage.render,
                                                   "_master_gain_dB", None)
                debug["lufs_post_master"] = audio_meta.lufs_of(out_path)
                debug["mastering_applied"] = True
                debug["mastering_quality_score"] = \
                    director._compute_mastering_quality_score(
                        master_lufs, debug["lufs_post_master"])
            except Exception as e:
                debug.setdefault("warnings", []).append(
                    f"mastering measurement skipped (kept video): {e}")
                debug["mastering_applied"] = True
                debug["target_lufs"] = master_lufs
                debug["lufs_pre_master"] = None
                debug["master_gain_dB"] = None
                debug["lufs_post_master"] = None
                debug["mastering_quality_score"] = None
        else:
            debug["mastering_applied"] = False
            debug["target_lufs"] = None
            debug["lufs_pre_master"] = None
            debug["master_gain_dB"] = None
            debug["lufs_post_master"] = None
            debug["mastering_quality_score"] = None

        _LAST_MUSIC_DEBUG = debug

    # Nettoyage du fichier pre-master conservé pour les mesures (s'il existe)
    premaster = getattr(montage.render, "_premaster_path", None)
    if premaster and os.path.exists(premaster):
        try:
            os.remove(premaster)
        except OSError:
            pass

    return out_path
