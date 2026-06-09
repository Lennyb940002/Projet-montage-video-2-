from backend import ffmpeg
from backend.pipeline import audio_meta


def _sine(path, freq, dur, vol_db=0):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", f"sine=frequency={freq}:duration={dur}",
                "-af", f"volume={vol_db}dB", path])


def test_lufs_plausible(tmp_path):
    f = str(tmp_path / "s.wav")
    _sine(f, 1000, 2)
    v = audio_meta.lufs_of(f)
    assert isinstance(v, float)
    assert -50.0 < v < 10.0


def test_lufs_quieter_audio_has_lower_lufs(tmp_path):
    loud = str(tmp_path / "l.wav"); quiet = str(tmp_path / "q.wav")
    _sine(loud, 1000, 2, 0)
    _sine(quiet, 1000, 2, -20)
    assert audio_meta.lufs_of(loud) > audio_meta.lufs_of(quiet) + 10


def test_dominance_voice_louder(tmp_path):
    voice = str(tmp_path / "v.wav"); mix = str(tmp_path / "m.wav")
    _sine(voice, 1000, 2, 0)
    _sine(mix, 1000, 2, -20)
    d = audio_meta.measure_dominance(mix, voice, [(0.0, 2.0)])
    assert d > 6.0


def test_dominance_music_too_loud(tmp_path):
    voice = str(tmp_path / "v.wav"); mix = str(tmp_path / "m.wav")
    _sine(voice, 1000, 2, -20)
    _sine(mix, 1000, 2, 0)
    d = audio_meta.measure_dominance(mix, voice, [(0.0, 2.0)])
    assert d < 6.0


def test_dominance_zero_when_no_active_ranges(tmp_path):
    voice = str(tmp_path / "v.wav"); mix = str(tmp_path / "m.wav")
    _sine(voice, 1000, 1); _sine(mix, 1000, 1)
    assert audio_meta.measure_dominance(mix, voice, []) == 0.0


# ---------- Mesure perceptive (voix isolée vs musique isolée traitée) ----------

def _mix_voice_and_music(voice, music, mix_out, voice_vol="0dB", music_vol="0dB"):
    """Crée un fichier 'mix' = voix + musique au volume choisi."""
    ffmpeg.run([
        ffmpeg.FFMPEG, "-y", "-i", voice, "-i", music,
        "-filter_complex",
        f"[0:a]volume={voice_vol}[v];[1:a]volume={music_vol}[m];"
        f"[v][m]amix=inputs=2:normalize=0:duration=longest[out]",
        "-map", "[out]", "-ac", "1", "-ar", "16000", mix_out,
    ])


def test_perceptive_dominance_voice_clearly_louder_than_music(tmp_path):
    """Voix 0 dB + musique très faible (-30 dB) -> dominance perceptive >> 6 dB."""
    voice = str(tmp_path / "v.wav"); music = str(tmp_path / "m.wav")
    mix = str(tmp_path / "mix.wav")
    _sine(voice, 1000, 3, vol_db=0)        # voix au max
    _sine(music, 400, 3, vol_db=-30)       # musique très faible
    _mix_voice_and_music(voice, music, mix)
    d = audio_meta.measure_dominance_perceptive(mix, voice, [(0.0, 3.0)])
    assert d > 6.0, f"expected > 6 dB, got {d:.2f}"


def test_perceptive_dominance_music_louder_than_voice(tmp_path):
    """Voix très faible + musique forte -> dominance perceptive bien < 6 dB."""
    voice = str(tmp_path / "v.wav"); music = str(tmp_path / "m.wav")
    mix = str(tmp_path / "mix.wav")
    _sine(voice, 1000, 3, vol_db=-30)
    _sine(music, 400, 3, vol_db=0)
    _mix_voice_and_music(voice, music, mix)
    d = audio_meta.measure_dominance_perceptive(mix, voice, [(0.0, 3.0)])
    assert d < 6.0, f"expected < 6 dB, got {d:.2f}"


def test_perceptive_dominance_returns_zero_without_ranges(tmp_path):
    voice = str(tmp_path / "v.wav"); mix = str(tmp_path / "m.wav")
    _sine(voice, 1000, 1); _sine(mix, 1000, 1)
    assert audio_meta.measure_dominance_perceptive(mix, voice, []) == 0.0


def test_perceptive_dominance_resistant_to_voice_in_mix(tmp_path):
    """Cas critique : voix 0 dB + musique faible (-12 dB).
    L'ancienne métrique RMS(voix) - RMS(mix) est ≈ 0 dB (mix contient la voix).
    La nouvelle métrique perceptive doit révéler que la voix DOMINE largement."""
    voice = str(tmp_path / "v.wav"); music = str(tmp_path / "m.wav")
    mix = str(tmp_path / "mix.wav")
    _sine(voice, 1000, 3, vol_db=0)
    _sine(music, 400, 3, vol_db=-12)
    _mix_voice_and_music(voice, music, mix)
    # Comparaison directe ancienne vs nouvelle
    old = audio_meta.measure_dominance(mix, voice, [(0.0, 3.0)])
    new = audio_meta.measure_dominance_perceptive(mix, voice, [(0.0, 3.0)])
    # L'ancienne mesure est biaisée vers 0, la nouvelle révèle la dominance réelle
    assert new > old + 5.0, (f"perceptive ({new:.1f}) doit être nettement supérieure "
                              f"à RMS-brut ({old:.1f}) qui souffre du biais voix-dans-mix")
    assert new > 6.0
