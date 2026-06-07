from backend.pipeline import sfx
from backend import ffmpeg

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

def test_choose_prefers_short(tmp_path):
    sub = tmp_path / "Impacts"; sub.mkdir()
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-i", "sine=f=200:d=0.3", str(sub / "court.wav")])
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-i", "sine=f=200:d=2.0", str(sub / "long.wav")])
    assert sfx.choose("impact", str(tmp_path)).endswith("court.wav")

def test_onset_detects_leadin(tmp_path):
    sub = tmp_path / "Impacts"; sub.mkdir()
    f = str(sub / "lead.wav")
    # 0.5 s de silence puis un son
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-i", "sine=f=300:d=0.3",
                "-af", "adelay=500|500", f])
    assert sfx.onset(f) > 0.3
