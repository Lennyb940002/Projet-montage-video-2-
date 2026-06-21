import os
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")
IMG = os.path.join(FIX, "sample_insert.png")
VID = os.path.join(FIX, "sample_insert.mp4")


def test_silent_mechanics_lists_v1():
    data = client.get("/silent/mechanics").json()
    names = {m["name"] for m in data}
    # noyau + concepts Tier 1
    assert {"comparison", "vote", "revelation", "collection", "elimination",
            "top3", "pov", "battle", "comparison_4"} <= names


def test_silent_generate_produces_video(tmp_path):
    out = str(tmp_path / "gen.mp4")
    r = client.post("/silent/generate", json={
        "goal": "engagement", "mechanic": "comparison",
        "assets": [IMG, VID], "seed": 9, "out_path": out})
    body = r.json()
    assert os.path.exists(body["video_path"])
    assert body["recipe"]["mechanic"] == "comparison"


def test_silent_generate_batch_produces_count_videos():
    # count>1 -> {videos:[...]} ; P3 : autant de vidéos que demandé.
    # mécanique forcée -> robuste vs historique accumulé en DB.
    r = client.post("/silent/generate", json={
        "goal": "engagement", "mechanic": "comparison",
        "assets": [IMG, VID], "seed": 100, "count": 3})
    body = r.json()
    assert "videos" in body and len(body["videos"]) == 3
    assert all(os.path.exists(v["video_path"]) for v in body["videos"])
    assert all(v["recipe"]["mechanic"] == "comparison" for v in body["videos"])
