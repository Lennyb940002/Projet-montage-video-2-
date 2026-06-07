import os, uuid
from dataclasses import asdict
from backend.config import WORKDIR
from backend.pipeline import transcribe as T
from backend.pipeline import audio_clean, align, subtitles, montage, detect, waveform

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

def make_video(clean_path, text, out_path, style="karaoke_yellow"):
    """Aligne le texte (corrigé) sur l'audio nettoyé, génère sous-titres + vidéo."""
    words, duration = T.transcribe(clean_path)
    tokens, n_sent = align.tokenize(text)
    align.align(tokens, words)
    job = os.path.dirname(clean_path)
    ass = os.path.join(job, "subs.ass")
    subtitles.build_ass(tokens, n_sent, ass, style=style)
    ranges = montage.sentence_ranges(tokens, n_sent, duration)
    montage.render(clean_path, ass, ranges, out_path)
    return out_path
