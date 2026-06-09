from backend.pipeline import music_bank


def test_validate_empty_lib(tmp_path):
    res = music_bank.validate_library(str(tmp_path))
    assert res["ok"] is False
    assert set(res["missing_categories"]) == {"Luxury", "Hype"}
    assert res["tracks_found"] == {"Luxury": 0, "Hype": 0}


def test_validate_partial_lib_luxury_only_complete(tmp_path):
    """Luxury complète (≥3), Hype vide -> seul Hype manque."""
    (tmp_path / "Luxury").mkdir()
    for n in range(3):
        (tmp_path / "Luxury" / f"a{n}.mp3").write_bytes(b"x")
    res = music_bank.validate_library(str(tmp_path))
    assert res["ok"] is False
    assert res["missing_categories"] == ["Hype"]
    assert res["tracks_found"] == {"Luxury": 3, "Hype": 0}


def test_validate_partial_lib_under_threshold_counts_as_missing(tmp_path):
    """Luxury sous le seuil (2 < 3) ET Hype vide -> les DEUX sont manquantes."""
    (tmp_path / "Luxury").mkdir()
    (tmp_path / "Luxury" / "a.mp3").write_bytes(b"x")
    (tmp_path / "Luxury" / "b.mp3").write_bytes(b"x")
    res = music_bank.validate_library(str(tmp_path))
    assert res["ok"] is False
    assert set(res["missing_categories"]) == {"Luxury", "Hype"}
    assert res["tracks_found"] == {"Luxury": 2, "Hype": 0}


def test_validate_full_lib(tmp_path):
    for cat in ("Luxury", "Hype"):
        d = tmp_path / cat
        d.mkdir()
        for n in range(3):
            (d / f"t{n}.mp3").write_bytes(b"x")
    res = music_bank.validate_library(str(tmp_path))
    assert res["ok"] is True
    assert res["missing_categories"] == []
    assert res["tracks_found"] == {"Luxury": 3, "Hype": 3}


def test_validate_unsupported_files_are_ignored(tmp_path):
    d = tmp_path / "Luxury"
    d.mkdir()
    (d / "a.mp3").write_bytes(b"x")
    (d / "b.txt").write_bytes(b"x")   # non supporté
    (d / ".hidden.mp3").write_bytes(b"x")   # ignoré
    res = music_bank.validate_library(str(tmp_path))
    assert res["tracks_found"]["Luxury"] == 1
