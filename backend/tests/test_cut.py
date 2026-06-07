import os
from backend.pipeline.audio_clean import cut_audio
from backend import ffmpeg

def test_cut_removes_range(sample_audio, tmp_path):
    out = str(tmp_path / "cut.mp3")
    before = ffmpeg.probe_duration(sample_audio)
    # enlève 2 secondes au milieu
    cut_audio(sample_audio, out, [(2.0, 4.0)])
    after = ffmpeg.probe_duration(out)
    assert os.path.exists(out)
    assert abs((before - 2.0) - after) < 0.6   # ~2 s en moins

def test_cut_no_range_is_copy(sample_audio, tmp_path):
    out = str(tmp_path / "copy.mp3")
    cut_audio(sample_audio, out, [])
    assert abs(ffmpeg.probe_duration(out) - ffmpeg.probe_duration(sample_audio)) < 0.5
