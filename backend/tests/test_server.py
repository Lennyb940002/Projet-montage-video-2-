import os
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_load_and_preview(sample_audio, tmp_path):
    r = client.post("/load", json={"audio_path": sample_audio})
    data = r.json()
    assert "montre" in data["transcript"].lower()
    assert data["duration"] > 5
    out = str(tmp_path / "preview.mp4")
    r2 = client.post("/preview", json={"clean_path": data["clean_path"],
                                       "text": data["transcript"], "out_path": out})
    assert os.path.exists(r2.json()["video_path"])
