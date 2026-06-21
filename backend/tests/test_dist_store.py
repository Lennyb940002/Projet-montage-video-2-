from backend.distribution.store import DistStore


def test_insert_and_get(tmp_path):
    s = DistStore(str(tmp_path / "d.db"))
    pid = s.insert(video_path="v.mp4", mechanic="comparison", content_angle="a_or_b",
                   layout="split_2", asset_ids=["a", "b"], caption="cap")
    row = s.get(pid)
    assert row["status"] == "pending" and row["video_path"] == "v.mp4"


def test_update_status_and_query_pending(tmp_path):
    s = DistStore(str(tmp_path / "d.db"))
    p1 = s.insert(video_path="v1", mechanic="vote", content_angle="x", layout="split_2",
                  asset_ids=["a"], caption="c")
    s.insert(video_path="v2", mechanic="vote", content_angle="y", layout="split_2",
             asset_ids=["b"], caption="c")
    s.update_status(p1, "posted")
    pend = s.query_pending()
    assert len(pend) == 1 and pend[0]["video_path"] == "v2"
    assert s.get(p1)["status"] == "posted"


def test_recent_models_and_music(tmp_path):
    s = DistStore(str(tmp_path / "d.db"))
    s.insert(video_path="v1", mechanic="comparison", content_angle="a", layout="split_2",
             asset_ids=["C:/Bank/GMT/x.mp4", "C:/Bank/Ruby/y.mp4"], caption="c",
             music="C:/Music/song1.mp3")
    s.insert(video_path="v2", mechanic="vote", content_angle="b", layout="split_2",
             asset_ids=["C:/Bank/Saphir/z.mp4"], caption="c", music="C:/Music/song2.mp3")
    # recent_models(1) = montres de la dernière vidéo seulement
    assert s.recent_models(1) == {"Saphir"}
    # recent_models(2) = montres des 2 dernières
    assert s.recent_models(2) == {"GMT", "Ruby", "Saphir"}
    assert s.recent_music(1) == {"C:/Music/song2.mp3"}
    assert s.recent_music(2) == {"C:/Music/song1.mp3", "C:/Music/song2.mp3"}
