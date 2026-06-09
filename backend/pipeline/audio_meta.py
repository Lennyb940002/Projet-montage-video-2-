"""Mesures audio réutilisables : LUFS (loudness) et dominance voix vs mix."""
import random
import re

from backend import ffmpeg


def lufs_of(path):
    """LUFS intégrée du fichier via ebur128. Fallback -23.0 si parse échoue.

    ebur128 émet plusieurs lignes 'I: ... LUFS' au fil de l'analyse + une ligne
    de threshold qui matche le même motif. Le résumé final est dans le bloc
    'Integrated loudness'. On prend la DERNIÈRE valeur 'I: X LUFS' (résumé)
    pour fiabilité.
    """
    r = ffmpeg.run([ffmpeg.FFMPEG, "-i", path, "-af", "ebur128=peak=true",
                    "-f", "null", "-"])
    matches = re.findall(r"I:\s*(-?[0-9.]+)\s*LUFS", r.stderr)
    if not matches:
        return -23.0
    try:
        return float(matches[-1])
    except (ValueError, IndexError):
        return -23.0


def _rms_db(path, start, end):
    """RMS (dBFS) d'une fenêtre [start, end] du fichier audio."""
    r = ffmpeg.run([ffmpeg.FFMPEG, "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                    "-i", path, "-af", "astats=metadata=1:reset=1",
                    "-f", "null", "-"])
    m = re.search(r"RMS level dB:\s*(-?[0-9.]+)", r.stderr)
    try:
        return float(m.group(1)) if m else -90.0
    except (ValueError, AttributeError):
        return -90.0


def measure_dominance(mix_path, voice_path, voice_active_ranges,
                      sample_dur=0.2, n_samples=5, rng_seed=123):
    """Dominance moyenne (dB) de la voix sur le mix, mesurée sur n_samples
    fenêtres de sample_dur secondes prises au hasard dans les plages
    voice_active_ranges.

    Renvoie 0.0 si aucune plage utilisable (cas dégénéré).
    """
    if not voice_active_ranges:
        return 0.0
    rng = random.Random(rng_seed)
    picks = []
    for _ in range(n_samples):
        s, e = rng.choice(voice_active_ranges)
        if e - s < sample_dur:
            continue
        t0 = rng.uniform(s, e - sample_dur)
        picks.append((t0, t0 + sample_dur))
    if not picks:
        return 0.0
    diffs = []
    for s, e in picks:
        diffs.append(_rms_db(voice_path, s, e) - _rms_db(mix_path, s, e))
    return sum(diffs) / len(diffs)
