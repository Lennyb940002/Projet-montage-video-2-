from backend.pipeline.waveform import peaks

def test_peaks_shape(sample_audio):
    p = peaks(sample_audio, buckets=400)
    assert 100 < len(p) <= 400
    assert all(0.0 <= x <= 1.0 for x in p)
    assert max(p) > 0.1   # il y a du signal
