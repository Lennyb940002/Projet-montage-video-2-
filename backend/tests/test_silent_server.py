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
    assert names == {"comparison", "vote", "revelation"}


def test_silent_generate_produces_video(tmp_path):
    out = str(tmp_path / "gen.mp4")
    r = client.post("/silent/generate", json={
        "goal": "engagement", "mechanic": "comparison",
        "assets": [IMG, VID], "seed": 9, "out_path": out})
    body = r.json()
    assert os.path.exists(body["video_path"])
    assert body["recipe"]["mechanic"] == "comparison"
