import os
from backend.pipeline.audio_clean import remove_silences
from backend import ffmpeg

def test_remove_silences_shortens(sample_audio, tmp_path):
    out = str(tmp_path / "clean.mp3")
    result = remove_silences(sample_audio, out)
    assert os.path.exists(result)
    before = ffmpeg.probe_duration(sample_audio)
    after = ffmpeg.probe_duration(result)
    assert after <= before          # jamais plus long
    assert after > before * 0.4     # mais pas vidé
