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
    """Dominance "brute" (legacy) : RMS(voix) - RMS(mix) sur les fenêtres
    voice_active. Biaisée vers 0 parce que le mix contient la voix.
    Conservée pour rétro-compatibilité ; pour la vraie évaluation produit,
    utiliser `measure_dominance_perceptive`.
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


def _isolate_music_from_mix(mix_path, voice_path, out_path):
    """Isole la musique traitée du mix par soustraction par inversion de phase.

    Principe :
       inverse(voice) + mix ≈ music_treated
    (la voix présente dans le mix s'annule avec la voix inversée alignée).

    NB : la précision dépend de l'alignement exact voix/mix dans le temps.
    Comme la voix est utilisée TELLE QUELLE dans le mix (pas re-encodée),
    l'alignement est parfait à l'échantillon près.
    """
    fc = (
        "[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo:sample_rates=48000,"
        "volume=-1.0[vinv];"
        "[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo:sample_rates=48000[mfix];"
        "[mfix][vinv]amix=inputs=2:normalize=0:duration=longest[out]"
    )
    r = ffmpeg.run([
        ffmpeg.FFMPEG, "-y", "-i", mix_path, "-i", voice_path,
        "-filter_complex", fc, "-map", "[out]",
        "-ac", "1", "-ar", "16000", out_path,
    ])
    return r.returncode == 0


def measure_dominance_perceptive(mix_path, voice_path, voice_active_ranges,
                                 sample_dur=0.2, n_samples=5, rng_seed=123):
    """Dominance perceptive (dB) = RMS(voix isolée) - RMS(musique isolée traitée)
    mesurée sur les fenêtres voice_active.

    La musique isolée est extraite du mix par soustraction par inversion de phase
    de la voix (voix + mix avec voix inversée → ~musique post-traitement).

    Renvoie 0.0 si aucune plage utilisable.
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

    # Génère un fichier "musique isolée" temporaire (1 seule fois)
    import os, tempfile, uuid
    tmp_dir = tempfile.gettempdir()
    music_only = os.path.join(tmp_dir, f"music_iso_{uuid.uuid4().hex}.wav")
    try:
        if not _isolate_music_from_mix(mix_path, voice_path, music_only):
            # En cas d'échec, fallback sur la mesure brute (pas de blocage)
            return measure_dominance(mix_path, voice_path, voice_active_ranges,
                                      sample_dur, n_samples, rng_seed)
        diffs = []
        for s, e in picks:
            rms_v = _rms_db(voice_path, s, e)
            rms_m = _rms_db(music_only, s, e)
            diffs.append(rms_v - rms_m)
        return sum(diffs) / len(diffs) if diffs else 0.0
    finally:
        try:
            if os.path.exists(music_only):
                os.remove(music_only)
        except OSError:
            pass
