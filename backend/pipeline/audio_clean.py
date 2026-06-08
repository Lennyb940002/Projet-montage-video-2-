import re
from backend import ffmpeg
from backend.config import SILENCE

def peak_db(audio_path):
    """Niveau crête (dBFS) du fichier via ffmpeg volumedetect. Fallback -3 dB."""
    r = ffmpeg.run([ffmpeg.FFMPEG, "-i", audio_path, "-af", "volumedetect", "-f", "null", "-"])
    m = re.search(r"max_volume:\s*(-?[0-9.]+)\s*dB", r.stderr)
    try:
        return float(m.group(1)) if m else -3.0
    except (ValueError, AttributeError):
        return -3.0

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
    """Resserre les silences avec un seuil ADAPTATIF (plancher de bruit + marge),
    borné dans une plage sûre, en conservant un souffle. Ne retire que ce qui est
    sous le seuil -> jamais de parole."""
    s = SILENCE
    thr_db = peak_db(audio_path) - s["below_peak"]              # seuil sous le pic réel
    thr_db = min(s["floor_max"], max(s["floor_min"], thr_db))   # clamp [floor_min, floor_max]
    thr = f"{thr_db:.0f}dB"
    keep = s["keep"]
    sr = (f"silenceremove=start_periods=1:start_duration=0:start_threshold={thr}:"
          f"stop_periods=-1:stop_duration={keep}:stop_threshold={thr}:detection=rms")
    r = ffmpeg.run([ffmpeg.FFMPEG, "-y", "-i", audio_path, "-af", sr,
                    "-c:a", "libmp3lame", "-q:a", "2", out_path])
    if r.returncode != 0:
        raise RuntimeError(f"silenceremove a échoué: {r.stderr[-300:]}")
    return out_path
