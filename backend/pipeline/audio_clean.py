from backend import ffmpeg
from backend.config import SILENCE

def remove_silences(audio_path, out_path):
    """Resserre les silences (keep max 0.10 s, seuil -35dB). Réversible côté
    appelant (on garde l'original)."""
    keep = SILENCE["keep"]; thr = SILENCE["threshold"]
    sr = (f"silenceremove=start_periods=1:start_duration=0:start_threshold={thr}:"
          f"stop_periods=-1:stop_duration={keep}:stop_threshold={thr}:detection=rms")
    r = ffmpeg.run([ffmpeg.FFMPEG, "-y", "-i", audio_path, "-af", sr,
                    "-c:a", "libmp3lame", "-q:a", "2", out_path])
    if r.returncode != 0:
        raise RuntimeError(f"silenceremove a échoué: {r.stderr[-300:]}")
    return out_path
