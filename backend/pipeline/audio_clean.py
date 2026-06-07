from backend import ffmpeg
from backend.config import SILENCE

def cut_audio(audio_path, out_path, remove_ranges):
    """Retire des plages temporelles [(start, end), ...] de l'audio (garde le
    complément), puis ré-encode. remove_ranges vide = simple copie."""
    dur = ffmpeg.probe_duration(audio_path)
    # construit les segments à GARDER (complément des plages à retirer)
    keeps = []
    cur = 0.0
    for s, e in sorted(remove_ranges):
        s = max(0.0, s); e = min(dur, e)
        if s > cur:
            keeps.append((cur, s))
        cur = max(cur, e)
    if cur < dur:
        keeps.append((cur, dur))
    if not keeps:
        keeps = [(0.0, dur)]
    parts = []
    labels = []
    for k, (s, e) in enumerate(keeps):
        parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=N/SR/TB[a{k}]")
        labels.append(f"[a{k}]")
    filt = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(keeps)}:v=0:a=1[out]"
    r = ffmpeg.run([ffmpeg.FFMPEG, "-y", "-i", audio_path, "-filter_complex", filt,
                    "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "2", out_path])
    if r.returncode != 0:
        raise RuntimeError(f"cut_audio a échoué: {r.stderr[-300:]}")
    return out_path

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
