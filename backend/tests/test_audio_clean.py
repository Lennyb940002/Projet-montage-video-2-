import os
from backend.pipeline.audio_clean import remove_silences, peak_db
from backend import ffmpeg

def test_peak_db_plausible(sample_audio):
    p = peak_db(sample_audio)
    assert isinstance(p, float)
    assert -40.0 < p < 1.0

def test_remove_silences_shortens(sample_audio, tmp_path):
    out = str(tmp_path / "clean.mp3")
    result = remove_silences(sample_audio, out)
    assert os.path.exists(result)
    before = ffmpeg.probe_duration(sample_audio)
    after = ffmpeg.probe_duration(result)
    assert after <= before          # jamais plus long
    assert after > before * 0.4     # mais pas vidé
