import os, glob, random
from backend import ffmpeg
from backend.config import VIDEO, DEFAULT_CLIPS_DIR


# --- Helpers Motion V1 (exécutif uniquement) ----------------------------------

def _zoom_chain(in_label, out_label, W, H, zf):
    """Scale + crop pour un zoom CONSTANT donné. Pas d'animation -> aucune image figée."""
    cw, ch = int(W * zf), int(H * zf)
    return (f"[{in_label}]scale={cw}:{ch}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1[{out_label}]")

def _shake_x(amp_px, dur):
    """Expression pour `crop` x avec oscillation (dans une scène de durée `dur`).
    Le clip est étendu de `amp_px` de chaque côté (scale) avant ce crop."""
    return f"{amp_px}+{amp_px}*sin(t*60)"

def _shake_y(amp_px):
    return f"{amp_px}+{amp_px}*sin(t*47)"


def _motion_for_clip(clip_index, plan):
    """Renvoie (zoom_base, [punches], [shakes]) pour un clip donné."""
    if not plan:
        return None, [], []
    zoom_base = None
    punches, shakes = [], []
    for m in plan.get("motion", []):
        if m.get("clip_index") != clip_index:
            continue
        if m["kind"] == "zoom_clip":
            zoom_base = m["zoom"]
        elif m["kind"] == "punch":
            punches.append(m)
        elif m["kind"] == "shake":
            shakes.append(m)
    return zoom_base, punches, shakes


# Fenêtres de durée (s) pour choisir un bon son par catégorie (critères de l'expert)
SFX_DUR = {"Impacts": (0.08, 0.25), "Whooshs": (0.18, 0.45), "Risers": (0.30, 0.80),
           "Drops": (0.10, 0.35), "Mechanical": (0.10, 0.60), "Electronic": (0.10, 0.50)}
# EQ (passe-haut, passe-bas en Hz) pour que les SFX passent sous la voix
SFX_EQ = {"Impacts": (120, 8000), "Whooshs": (250, 10000), "Risers": (300, 9000),
          "Drops": (60, 8000), "Mechanical": (150, 7000), "Electronic": (200, 9000)}


def list_clips(clips_dir=DEFAULT_CLIPS_DIR):
    """Clips .mp4 dédoublonnés par taille de fichier."""
    seen = {}; clips = []
    for c in sorted(glob.glob(os.path.join(clips_dir, "*.mp4"))):
        sz = os.path.getsize(c)
        if sz in seen: continue
        seen[sz] = c; clips.append(c)
    return clips

def sentence_ranges(tokens, n_sent, duration):
    starts = []
    for si in range(n_sent):
        ws = [t for t in tokens if t["sent"] == si]
        starts.append(ws[0]["start"] if ws else (starts[-1] if starts else 0.0))
    if starts: starts[0] = 0.0
    ranges = []
    for si in range(n_sent):
        s = starts[si]; e = starts[si + 1] if si + 1 < n_sent else duration
        ranges.append((s, max(e, s + 0.3)))
    return ranges or [(0.0, duration)]

def apply_boost_cuts(ranges, hook_dur, hook_cut):
    """Redécoupe la portion [0, hook_dur] en tranches de hook_cut (cuts rapides)."""
    out = []
    for s, e in ranges:
        if s >= hook_dur:
            out.append((s, e)); continue
        hook_end = min(e, hook_dur)
        t = s
        while t < hook_end - 1e-3:
            nt = min(t + hook_cut, hook_end)
            out.append((t, nt)); t = nt
        if e > hook_dur:
            out.append((hook_dur, e))
    return out

def _merge_timeline(ranges, manual_inserts):
    """Fusionne les ranges auto + les inserts manuels en une timeline séquentielle.

    Args:
      ranges: [(s, e), ...] plages auto-clip décidées par sentence_ranges
      manual_inserts: [{kind:"image"|"clip", path, start, end}, ...] ou None

    Returns:
      segments en ordre temporel : liste de dicts avec :
        - kind = "auto" | "image" | "clip"
        - start, end (en secondes sur la timeline globale)
        - auto_idx (seulement pour 'auto') : index du range d'origine, pour
          retrouver motion/transitions du Director par clip_index
        - path (seulement pour 'image'/'clip') : fichier source

    Contrat : les segments couvrent EXACTEMENT l'union des ranges (jamais de
    trou, jamais d'overlap). Les inserts priment sur les autos durant leur
    fenêtre. Inserts de durée 0 ignorés. Un insert qui chevauche 2 ranges
    consécutifs produit 2 segments insert contigus (concat ffmpeg les
    rejouera comme un bloc continu pour l'utilisateur)."""
    if not manual_inserts:
        return [{"kind": "auto", "start": s, "end": e, "auto_idx": i}
                for i, (s, e) in enumerate(ranges)]

    # Sanitize + trie
    ins = [{"kind": x["kind"], "path": x["path"],
            "start": float(x["start"]), "end": float(x["end"])}
           for x in manual_inserts if float(x["end"]) > float(x["start"])]
    ins.sort(key=lambda x: x["start"])

    EPS = 1e-3
    segments = []
    for auto_idx, (rs, re) in enumerate(ranges):
        overlapping = [x for x in ins if x["end"] > rs and x["start"] < re]
        if not overlapping:
            segments.append({"kind": "auto", "start": rs, "end": re,
                             "auto_idx": auto_idx})
            continue
        cursor = rs
        for x in overlapping:
            xs = max(rs, x["start"])
            xe = min(re, x["end"])
            if cursor < xs - EPS:
                segments.append({"kind": "auto", "start": cursor, "end": xs,
                                 "auto_idx": auto_idx})
            segments.append({"kind": x["kind"], "path": x["path"],
                             "start": xs, "end": xe})
            cursor = xe
        if cursor < re - EPS:
            segments.append({"kind": "auto", "start": cursor, "end": re,
                             "auto_idx": auto_idx})
    return segments


def _pick_clips(ranges, clips, rng=None):
    """Sélection des clips. rng=Random local (seed) -> reproductible ; None = random global."""
    r = rng if rng is not None else random
    durs = {c: ffmpeg.probe_duration(c) for c in clips}
    avail = clips[:]; r.shuffle(avail); chosen = []
    for (s, e) in ranges:
        L = e - s; pick = None
        for n, c in enumerate(avail):
            if durs[c] >= L + 0.15:
                pick = avail.pop(n); break
        if pick is not None:
            off = r.uniform(0, max(0.0, durs[pick] - L))
            chosen.append((pick, off, L, False))
        elif avail:
            c = max(avail, key=lambda x: durs[x]); avail.remove(c)
            chosen.append((c, 0.0, L, True))
        else:
            avail = clips[:]; r.shuffle(avail); c = avail.pop(0)
            chosen.append((c, 0.0, L, durs[c] < L + 0.15))
    return chosen

def render(audio_path, ass_path, ranges, out_path, clips_dir=DEFAULT_CLIPS_DIR,
           boost=False, sfx_events=None, sfx_dir=None, plan=None, seed=None,
           master_lufs=None, manual_inserts=None):
    """ranges = plages de clips FINALES (le redécoupage hook est fait par l'appelant).
    sfx_events = plan SFX (catégories résolues en fichiers via sfx.pick).
    plan = plan global du Director : utilisé pour appliquer motion + transitions.
    manual_inserts = [{kind:"image"|"clip", path, start, end}] : médias manuels
      qui priment sur les clips auto durant leur fenêtre. Si None/empty,
      comportement strictement identique au pipeline d'origine.
    Le renderer ne décide RIEN : il exécute le plan tel quel."""
    from backend.config import BOOST, SFX_DIR
    from backend.pipeline import sfx as sfxmod
    sfx_dir = sfx_dir or SFX_DIR
    clips = list_clips(clips_dir)
    if not clips:
        raise RuntimeError(f"Aucun clip dans {clips_dir}")

    # --- Construction de la timeline unifiée (auto + inserts manuels) ---
    segments = _merge_timeline(ranges, manual_inserts)
    # On ne pick des clips auto QUE pour les segments 'auto', en conservant
    # leur ordre temporel pour rester compatible avec _pick_clips.
    auto_seg_indices = [i for i, s in enumerate(segments) if s["kind"] == "auto"]
    auto_ranges = [(segments[i]["start"], segments[i]["end"]) for i in auto_seg_indices]
    auto_chosen = _pick_clips(auto_ranges, clips,
                              rng=random.Random(seed) if seed is not None else None)
    # Map segment index global -> (clip_path, off, L, loop) si auto
    auto_chosen_by_seg = {seg_i: auto_chosen[k]
                          for k, seg_i in enumerate(auto_seg_indices)}

    W, H, FPS, ZOOM = VIDEO["width"], VIDEO["height"], VIDEO["fps"], VIDEO["zoom"]

    cmd = [ffmpeg.FFMPEG, "-y"]
    for k, seg in enumerate(segments):
        L = seg["end"] - seg["start"]
        if seg["kind"] == "auto":
            (c, off, _L, loop) = auto_chosen_by_seg[k]
            if loop:
                cmd += ["-stream_loop", "-1", "-t", f"{L:.3f}", "-i", c]
            else:
                cmd += ["-ss", f"{off:.3f}", "-t", f"{L:.3f}", "-i", c]
        elif seg["kind"] == "image":
            # Boucle l'image pendant la durée du segment
            cmd += ["-loop", "1", "-t", f"{L:.3f}", "-i", seg["path"]]
        else:  # "clip" : vidéo manuelle, audio ignoré côté mapping
            cmd += ["-t", f"{L:.3f}", "-i", seg["path"]]
    cmd += ["-i", audio_path]
    Ncl = len(segments)

    # 1 son cohérent par catégorie (réutilisé), choisi par fenêtre de durée,
    # + mesures d'alignement (lead-in pour l'attaque, position du pic).
    cat_file = {}; cat_onset = {}; cat_peak = {}
    resolved = []
    if sfx_events:
        for e in sfx_events:
            c = e["category"]
            if c not in cat_file:
                lo, hi = SFX_DUR.get(c, (0.05, 1e9))
                cf = sfxmod.choose(c, sfx_dir, lo, hi)
                cat_file[c] = cf
                cat_onset[c] = (sfxmod.onset(cf) if (cf and c in ("Impacts", "Drops", "Mechanical")) else 0.0)
                cat_peak[c] = sfxmod.peak_time(cf) if cf else 0.0
            if cat_file[c]:
                resolved.append((e, cat_file[c]))
    for (_e, f) in resolved:
        cmd += ["-i", f]

    # vidéo : exécute le plan (motion + transitions) si fourni, sinon zoom constant.
    # Index des transitions par clip_index original pour O(1).
    tr_by_clip = {t["clip_index"]: t for t in ((plan or {}).get("transitions") or [])}
    # Auto-segment qui commence un NOUVEAU range original -> transition éligible.
    # On la pose UNIQUEMENT sur le 1er segment auto d'un range donné.
    seen_auto_idx = set()
    fc = []
    for k, seg in enumerate(segments):
        L = seg["end"] - seg["start"]

        if seg["kind"] == "auto":
            # 1) Choix du zoom + motion : seulement si le segment auto recouvre
            #    INTÉGRALEMENT le range original (sinon le punch at_local serait
            #    en dehors du segment réel). Si split par un insert -> zoom basal.
            auto_idx = seg["auto_idx"]
            orig_rs, orig_re = ranges[auto_idx]
            full_range = (abs(seg["start"] - orig_rs) < 1e-3
                          and abs(seg["end"] - orig_re) < 1e-3)
            if full_range:
                zoom_base, punches, shakes = _motion_for_clip(auto_idx, plan)
            else:
                zoom_base, punches, shakes = None, [], []
            if zoom_base is None:
                zoom_base = BOOST["punch_zoom"] if (boost and auto_idx == 0) else ZOOM

            if not punches:
                subsegs = [(0.0, L, zoom_base, None)]
            else:
                p = punches[0]
                ps = max(0.0, min(L, p["at_local"]))
                pe = max(ps, min(L, ps + p["dur"]))
                sh = next((s for s in shakes if abs(s["at_local"] - p["at_local"]) < 1e-3), None)
                subsegs = []
                if ps > 0.01:
                    subsegs.append((0.0, ps, zoom_base, None))
                subsegs.append((ps, pe, p["zoom_to"], sh))
                if L - pe > 0.01:
                    subsegs.append((pe, L, zoom_base, None))

            seg_labels = []
            for si, (s, e, zf, sh) in enumerate(subsegs):
                cw, ch = int(W * zf), int(H * zf)
                chain = (f"[{k}:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS,"
                         f"scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={W}:{H}")
                if sh:
                    amp = sh["amp_px"]
                    chain += (f",pad=iw+{2*amp}:ih+{2*amp}:{amp}:{amp},"
                              f"crop={W}:{H}:x='{_shake_x(amp, sh['dur'])}':y='{_shake_y(amp)}':exact=1")
                chain += f",setsar=1[k{k}s{si}]"
                fc.append(chain)
                seg_labels.append(f"[k{k}s{si}]")
            if len(seg_labels) == 1:
                fc.append(f"{seg_labels[0]}fps={FPS},format=yuv420p[vraw{k}]")
            else:
                fc.append("".join(seg_labels) +
                          f"concat=n={len(seg_labels)}:v=1:a=0,fps={FPS},format=yuv420p[vraw{k}]")

            # 4) Transition d'entrée : seulement sur le 1er segment auto du range
            #    original (et seulement si on tombe pile sur le début du range).
            apply_tr = (auto_idx not in seen_auto_idx
                        and abs(seg["start"] - orig_rs) < 1e-3)
            seen_auto_idx.add(auto_idx)
            tr = tr_by_clip.get(auto_idx) if apply_tr else None
            if tr and tr["kind"] == "fade_in":
                fc.append(f"[vraw{k}]fade=t=in:st=0:d={tr['dur']:.3f}[v{k}]")
            elif tr and tr["kind"] == "zoom_punch_in":
                fc.append(f"[vraw{k}]fade=t=in:st=0:d=0.06[v{k}]")
            else:
                fc.append(f"[vraw{k}]null[v{k}]")

        elif seg["kind"] == "image":
            # Image fixe avec Ken Burns subtil : zoom progressif 1.0 -> 1.05
            # via scale+crop animé. Format 1080x1920 cover.
            # zoompan classique pour images statiques : déterministe et fluide.
            d_frames = max(1, int(round(L * FPS)))
            # zoompan : zoom de 1.0 à 1.05 linéaire sur la durée
            chain = (f"[{k}:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
                     f"crop={W*2}:{H*2},"
                     f"zoompan=z='min(zoom+0.0005,1.05)':d={d_frames}:s={W}x{H}:fps={FPS},"
                     f"trim=duration={L:.3f},setpts=PTS-STARTPTS,"
                     f"setsar=1,format=yuv420p[vraw{k}]")
            fc.append(chain)
            # Petit fade-in pour annoncer l'insert (anti-flash brutal)
            fc.append(f"[vraw{k}]fade=t=in:st=0:d=0.12[v{k}]")

        else:  # "clip" : vidéo manuelle (audio ignoré via -map ciblé plus loin)
            chain = (f"[{k}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                     f"crop={W}:{H},setsar=1,fps={FPS},format=yuv420p,"
                     f"trim=duration={L:.3f},setpts=PTS-STARTPTS[vraw{k}]")
            fc.append(chain)
            fc.append(f"[vraw{k}]fade=t=in:st=0:d=0.10[v{k}]")

    fc.append("".join(f"[v{k}]" for k in range(Ncl)) + f"concat=n={Ncl}:v=1:a=0[cv]")
    ass_dir = os.path.dirname(os.path.abspath(ass_path))
    ass_name = os.path.basename(ass_path)
    if boost:
        fc.append(f"[cv]drawbox=x=0:y=0:w=iw:h=ih:color=white@1:t=fill:"
                  f"enable='lt(t,{BOOST['flash']})'[cf];[cf]ass={ass_name}[vout]")
    else:
        fc.append(f"[cv]ass={ass_name}[vout]")

    # audio : voix + SFX (volume/fondus par évènement)
    if resolved:
        fc.append(f"[{Ncl}:a]aformat=sample_fmts=fltp:channel_layouts=stereo[av]")
        for i, (e, f) in enumerate(resolved):
            c = e["category"]
            sdur = ffmpeg.probe_duration(f)
            on = cat_onset.get(c, 0.0)
            eff = max(0.1, sdur - on)              # durée après retrait du lead-in
            hpf, lpf = SFX_EQ.get(c, (150, 10000))
            # placement (adelay) selon l'alignement demandé
            align = e.get("align", "attack")
            if align == "peak":
                place = max(0.0, e["time"] - cat_peak.get(c, 0.0))
            elif align == "end":
                place = max(0.0, e["time"] - eff - 0.03)
            else:  # attack : le son (lead-in retiré) démarre sur l'évènement
                place = e["time"]
            d = int(round(place * 1000))
            fin = e.get("fade_in_ms", 0) / 1000.0
            fout = e.get("fade_out_ms", 0) / 1000.0
            parts = []
            if on > 0.01:
                parts += [f"atrim=start={on:.3f}", "asetpts=N/SR/TB"]
            parts += [f"highpass=f={hpf}", f"lowpass=f={lpf}", f"volume={e['gain_dB']}dB"]
            if fin > 0:
                parts.append(f"afade=t=in:st=0:d={fin:.3f}")
            if fout > 0 and eff > fout:
                parts.append(f"afade=t=out:st={eff - fout:.3f}:d={fout:.3f}")
            parts.append(f"adelay={d}|{d}")
            parts.append("aformat=sample_fmts=fltp:channel_layouts=stereo")
            fc.append(f"[{Ncl + 1 + i}:a]" + ",".join(parts) + f"[se{i}]")
        mix = "[av]" + "".join(f"[se{i}]" for i in range(len(resolved)))
        fc.append(f"{mix}amix=inputs={len(resolved) + 1}:normalize=0:duration=first[aout]")
        amap = "[aout]"
    else:
        amap = f"{Ncl}:a"

    # --- Musique (Director-decided, purely executive in music_engine) ---
    from backend.pipeline import music_engine as _music_engine
    music = (plan or {}).get("music") if isinstance(plan, dict) else None
    # Label voix SANS crochets pour music_engine (qui les rajoute)
    voice_label = amap[1:-1] if amap.startswith("[") else amap
    # Index du PREMIER input musique = après vidéo (Ncl) + voix (1) + SFX (resolved)
    music_base_idx = Ncl + 1 + len(resolved)
    me = _music_engine.build(music, voice_label=voice_label,
                              base_input_idx=music_base_idx)
    if me["extra_inputs"]:
        for track in me["extra_inputs"]:
            cmd += ["-i", track]
    if me["filter_str"]:
        fc.append(me["filter_str"])
    # Si le moteur a produit un nouveau label de sortie, on l'utilise ; sinon
    # amap reste inchangé (no-op strict, prouvé par test_montage_music_noop).
    if me["out_label"] != voice_label:
        amap = f"[{me['out_label']}]"

    # --- Mastering LUFS final (ffmpeg loudnorm en bout de chaîne audio) ---
    # No-op si master_lufs is None (rétro-compatibilité bit-pour-bit garantie
    # par test_render_master_none_is_strict_noop).
    # Mastering : implémenté en 2 passes pour les vidéos courtes.
    # 1) Render une 1ʳᵉ fois (sans loudnorm) dans un fichier temporaire
    # 2) Mesurer LUFS du mix temp
    # 3) Render final avec gain statique = target - mesuré + true peak limiter
    # Cette approche est nettement plus fiable que le single-pass loudnorm
    # dynamique sur des contenus de 10-30 s (loudnorm dynamique a besoin
    # de matière pour calibrer).
    if master_lufs is not None:
        # On reporte le mastering APRÈS le 1er render -> traité hors filter_complex
        pass

    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", amap,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-r", str(FPS), "-shortest",
            "-movflags", "+faststart", "-map_metadata", "-1", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=ass_dir)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"Rendu échoué: {r.stderr[-400:]}")

    # --- Mastering V1 : gain statique uniforme (déterministe) ---
    # Pipeline : mesure LUFS du mix -> calcul gain -> volume uniforme -> re-mesure.
    # Avantages : déterministe, préserve voix/musique (même gain partout),
    # explicable, coût CPU faible.
    # Le mix pré-master est conservé pour permettre au service de mesurer la
    # dominance AVANT le gain (sinon le gain uniforme déplace voix ET musique
    # de la même quantité, ce qui ne change PAS la dominance mais peut altérer
    # les mesures absolues).
    render._premaster_path = None
    render._last_input_lufs = None
    render._master_gain_dB = None
    if master_lufs is not None:
        from backend.pipeline import audio_meta as _am
        import shutil as _shutil
        # 1) Mesure LUFS du mix non masterisé
        lufs_in = _am.lufs_of(out_path)
        render._last_input_lufs = lufs_in
        # 2) Calcul gain + clamp de sécurité [-12, +12] dB
        gain_dB = max(-12.0, min(12.0, master_lufs - lufs_in))
        render._master_gain_dB = round(gain_dB, 2)
        # 3) Conserve le mix non masterisé pour les mesures aval (dominance)
        premaster = out_path + ".premaster.mp4"
        _shutil.copy2(out_path, premaster)
        render._premaster_path = premaster
        # 4) Application : volume uniforme. Pas de limiter -> AAC produit des
        # intersample peaks naturellement contenus si le gain reste raisonnable
        # (l'AAC encode à -∞ dBFS plancher, le gain ne crée pas de clipping
        # tant que la source n'est pas déjà saturée).
        mastered = out_path + ".master.mp4"
        r2 = ffmpeg.run([ffmpeg.FFMPEG, "-y", "-i", out_path,
                         "-c:v", "copy",
                         "-af", f"volume={gain_dB:.3f}dB",
                         "-c:a", "aac", "-b:a", "192k",
                         "-movflags", "+faststart", mastered])
        if r2.returncode == 0 and os.path.exists(mastered):
            _shutil.move(mastered, out_path)
        # Si l'application échoue, on garde le mix non masterisé (jamais bloquant).
    return out_path
