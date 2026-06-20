import os, random
import pytest
from backend.silent import sampler


def _make_clips(d, n):
    paths = []
    for i in range(n):
        p = os.path.join(d, f"watch_{i:03d}.mp4")
        open(p, "wb").write(b"x")
        paths.append(p)
    return paths


def test_sample_returns_requested_count(tmp_path):
    _make_clips(str(tmp_path), 5)
    out = sampler.sample({"count": 2, "filters": {}}, random.Random(1), str(tmp_path))
    assert len(out) == 2
    assert all(os.path.isfile(p) for p in out)


def test_sample_no_duplicates(tmp_path):
    _make_clips(str(tmp_path), 4)
    out = sampler.sample({"count": 3, "filters": {}}, random.Random(2), str(tmp_path))
    assert len(set(out)) == 3


def test_sample_seed_reproducible(tmp_path):
    _make_clips(str(tmp_path), 6)
    a = sampler.sample({"count": 2, "filters": {}}, random.Random(42), str(tmp_path))
    b = sampler.sample({"count": 2, "filters": {}}, random.Random(42), str(tmp_path))
    assert a == b


def test_sample_raises_if_not_enough_clips(tmp_path):
    _make_clips(str(tmp_path), 1)
    with pytest.raises(ValueError, match="not enough"):
        sampler.sample({"count": 2, "filters": {}}, random.Random(1), str(tmp_path))
