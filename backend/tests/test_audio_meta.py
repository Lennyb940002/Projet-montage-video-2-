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
