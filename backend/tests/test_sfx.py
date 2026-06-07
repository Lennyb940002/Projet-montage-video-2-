from backend.pipeline import sfx

def test_pick_matches_category(tmp_path):
    (tmp_path / "impact_boom.wav").write_bytes(b"x")
    (tmp_path / "whoosh1.mp3").write_bytes(b"x")
    assert sfx.pick("impact", str(tmp_path)).endswith("impact_boom.wav")
    assert sfx.pick("whoosh", str(tmp_path)).endswith("whoosh1.mp3")

def test_pick_none_when_absent(tmp_path):
    assert sfx.pick("riser", str(tmp_path)) is None

def test_list_sfx_empty_dir(tmp_path):
    assert sfx.list_sfx(str(tmp_path / "nope")) == []

def test_pick_in_subfolder(tmp_path):
    sub = tmp_path / "Impacts"; sub.mkdir()
    (sub / "Cinematic Boom.mp3").write_bytes(b"x")
    (tmp_path / "Whooshs").mkdir()
    (tmp_path / "Whooshs" / "Whoosh 1.wav").write_bytes(b"x")
    assert sfx.pick("impact", str(tmp_path)).endswith("Cinematic Boom.mp3")
    assert sfx.pick("whoosh", str(tmp_path)).endswith("Whoosh 1.wav")
