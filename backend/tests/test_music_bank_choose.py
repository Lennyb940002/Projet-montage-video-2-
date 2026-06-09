import os
import random

from backend import ffmpeg
from backend.pipeline import music_bank


def _mk(path, dur=40):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", f"sine=frequency=440:duration={dur}",
                "-af", "volume=-12dB", path])


def test_choose_returns_track_in_category(tmp_path):
    (tmp_path / "Luxury").mkdir()
    for n in ("a.mp3", "b.mp3", "c.mp3"):
        _mk(str(tmp_path / "Luxury" / n))
    t = music_bank.choose("Luxury", target_dur=10, root=str(tmp_path),
                          rng=random.Random(42))
    assert t.endswith(".mp3") and "Luxury" in t


def test_choose_deterministic_with_seed(tmp_path):
    (tmp_path / "Hype").mkdir()
    for n in ("a.mp3", "b.mp3", "c.mp3"):
        _mk(str(tmp_path / "Hype" / n))
    t1 = music_bank.choose("Hype", target_dur=10, root=str(tmp_path),
                           rng=random.Random(7))
    t2 = music_bank.choose("Hype", target_dur=10, root=str(tmp_path),
                           rng=random.Random(7))
    assert t1 == t2


def test_choose_different_seeds_can_differ(tmp_path):
    (tmp_path / "Hype").mkdir()
    for n in ("a.mp3", "b.mp3", "c.mp3"):
        _mk(str(tmp_path / "Hype" / n))
    results = {
        music_bank.choose("Hype", 10, root=str(tmp_path), rng=random.Random(s))
        for s in range(20)
    }
    # 3 candidats, 20 seeds : on devrait voir au moins 2 sélections distinctes
    assert len(results) >= 2


def test_choose_returns_none_when_empty(tmp_path):
    assert music_bank.choose("Luxury", target_dur=10, root=str(tmp_path)) is None


def test_index_caches_lufs(tmp_path):
    (tmp_path / "Luxury").mkdir()
    _mk(str(tmp_path / "Luxury" / "a.mp3"))
    idx1 = music_bank.index_category("Luxury", str(tmp_path))
    assert any("a.mp3" in k for k in idx1.keys())
    entry = next(iter(idx1.values()))
    assert "lufs" in entry and "dur" in entry and "mtime" in entry
    # un fichier cache doit exister
    assert os.path.isfile(os.path.join(str(tmp_path), ".music_index.json"))
    # 2e appel = lecture du cache (identique)
    idx2 = music_bank.index_category("Luxury", str(tmp_path))
    assert idx2 == idx1


def test_index_rescans_when_file_modified(tmp_path):
    p = tmp_path / "Luxury"; p.mkdir()
    f = str(p / "a.mp3"); _mk(f)
    idx1 = music_bank.index_category("Luxury", str(tmp_path))
    # modifier le mtime du fichier
    import time
    new_mtime = os.path.getmtime(f) + 100
    os.utime(f, (new_mtime, new_mtime))
    idx2 = music_bank.index_category("Luxury", str(tmp_path))
    # mtime mis à jour dans le cache
    assert next(iter(idx2.values()))["mtime"] != next(iter(idx1.values()))["mtime"]
