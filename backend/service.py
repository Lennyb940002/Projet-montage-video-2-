import os, uuid
from backend.config import WORKDIR
from backend.pipeline import transcribe as T
from backend.pipeline import audio_clean, align, subtitles, montage

def load_audio(audio_path):
    """Transcrit + nettoie les silences. Retourne dict {clean_path, transcript, duration}."""
    job = os.path.join(WORKDIR, uuid.uuid4().hex)
    os.makedirs(job, exist_ok=True)
    clean = os.path.join(job, "clean.mp3")
    audio_clean.remove_silences(audio_path, clean)
    words, duration = T.transcribe(clean)
    transcript = " ".join(w.text for w in words)
    return {"job": job, "clean_path": clean, "transcript": transcript,
            "duration": duration}

def make_video(clean_path, text, out_path):
    """Aligne le texte (corrigé) sur l'audio nettoyé, génère sous-titres + vidéo."""
    words, duration = T.transcribe(clean_path)
    tokens, n_sent = align.tokenize(text)
    align.align(tokens, words)
    job = os.path.dirname(clean_path)
    ass = os.path.join(job, "subs.ass")
    subtitles.build_ass(tokens, n_sent, ass)
    ranges = montage.sentence_ranges(tokens, n_sent, duration)
    montage.render(clean_path, ass, ranges, out_path)
    return out_path
