import os
from backend import ffmpeg

def test_binaries_exist():
    assert os.path.exists(ffmpeg.FFMPEG)
    assert os.path.exists(ffmpeg.FFPROBE)

def test_probe_duration(sample_audio):
    d = ffmpeg.probe_duration(sample_audio)
    assert 5 < d < 30  # sample ~13 s
