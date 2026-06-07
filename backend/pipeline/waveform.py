"""Calcul des pics d'amplitude pour dessiner la forme d'onde côté UI."""
import subprocess, array
from backend import ffmpeg

def peaks(audio_path, buckets=900):
    """Retourne une liste de pics 0..1 (max absolu par tranche)."""
    r = subprocess.run([ffmpeg.FFMPEG, "-v", "quiet", "-i", audio_path,
                        "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                       capture_output=True)
    raw = r.stdout
    if not raw:
        return []
    samples = array.array("h")
    samples.frombytes(raw[:len(raw) // 2 * 2])
    n = len(samples)
    if n == 0:
        return []
    size = max(1, -(-n // buckets))   # ceil -> au plus `buckets` tranches
    out = []
    for i in range(0, n, size):
        m = 0
        for s in samples[i:i + size]:
            a = s if s >= 0 else -s
            if a > m:
                m = a
        out.append(round(m / 32768, 4))
    return out
