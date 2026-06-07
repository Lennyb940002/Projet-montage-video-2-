import os, uuid
from dataclasses import asdict
from backend.config import WORKDIR
from backend.pipeline import transcribe as T
from backend.config import BOOST
from backend.pipeline import audio_clean, align, subtitles, montage, detect, waveform, sfx_plan

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

def make_video(clean_path, text, out_path, style="karaoke_yellow", boost=False):
    """Aligne le texte (corrigé) sur l'audio nettoyé, génère sous-titres + vidéo."""
    words, duration = T.transcribe(clean_path)
    tokens, n_sent = align.tokenize(text)
    align.align(tokens, words)
    job = os.path.dirname(clean_path)
    ass = os.path.join(job, "subs.ass")
    subtitles.build_ass(tokens, n_sent, ass, style=style)
    ranges = montage.sentence_ranges(tokens, n_sent, duration)

    sfx_events = None
    if boost:
        ranges = montage.apply_boost_cuts(ranges, BOOST["hook_dur"], BOOST["hook_cut"])
        # détection SFX sur le texte CORRIGÉ (meilleure orthographe -> meilleures marques)
        sw = [T.Word(t["disp"], t["start"], t["end"], 1.0) for t in tokens]
        phrases = []
        for si in range(n_sent):
            ts = [t for t in tokens if t["sent"] == si]
            if ts:
                phrases.append((ts[0]["start"], ts[-1]["end"]))
        cuts = [r[0] for r in ranges if r[0] > 0.01]
        sfx_events = sfx_plan.generate_sfx(sw, phrases, cuts, duration, BOOST["hook_dur"])

    montage.render(clean_path, ass, ranges, out_path, boost=boost, sfx_events=sfx_events)
    return out_path
