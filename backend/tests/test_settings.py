from backend import settings

def test_roundtrip(tmp_path):
    p = str(tmp_path / "s.json")
    settings.save({"ig_token": "T123", "ig_user_id": "42"}, path=p)
    d = settings.load(path=p)
    assert d["ig_token"] == "T123" and d["ig_user_id"] == "42"

def test_load_missing_returns_empty(tmp_path):
    assert settings.load(path=str(tmp_path / "nope.json")) == {}

def test_save_merges(tmp_path):
    p = str(tmp_path / "s.json")
    settings.save({"ig_token": "T"}, path=p)
    settings.save({"ig_user_id": "9"}, path=p)
    d = settings.load(path=p)
    assert d["ig_token"] == "T" and d["ig_user_id"] == "9"
