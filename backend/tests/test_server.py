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
    # Phase 2 : mots + détection présents
    assert len(data["words"]) > 5
    assert "prob" in data["words"][0]
    assert "retakes" in data["detect"] and "lowconf" in data["detect"]
    out = str(tmp_path / "preview.mp4")
    r2 = client.post("/preview", json={"clean_path": data["clean_path"],
                                       "text": data["transcript"], "out_path": out})
    assert os.path.exists(r2.json()["video_path"])

def test_load_missing_file_returns_json_error():
    safe = TestClient(app, raise_server_exceptions=False)
    r = safe.post("/load", json={"audio_path": "C:/nope/does_not_exist_123.mp3"})
    assert r.status_code == 500
    assert "error" in r.json()
    assert "introuvable" in r.json()["error"].lower()

def test_settings_roundtrip_api(monkeypatch, tmp_path):
    from backend import settings as sm
    monkeypatch.setattr(sm, "DEFAULT_PATH", str(tmp_path / "s.json"))
    r = client.post("/settings", json={"ig_token": "TOK", "ig_user_id": "123"})
    assert r.json() == {"ig_user_id": "123", "has_token": True}
    assert client.get("/settings").json()["has_token"] is True

def test_publish_requires_settings(monkeypatch, tmp_path):
    from backend import settings as sm
    monkeypatch.setattr(sm, "DEFAULT_PATH", str(tmp_path / "empty.json"))
    safe = TestClient(app, raise_server_exceptions=False)
    r = safe.post("/publish/instagram", json={"video_path": "x.mp4", "caption": "c"})
    assert r.status_code == 500 and "Réglages" in r.json()["error"]

def test_caption_endpoint():
    r = client.post("/caption", json={"text": "Pourquoi une Seiko ? Le prix est top. Écris SEIKO en commentaire."})
    data = r.json()
    assert "#seiko" in data["hashtags"]
    assert "full" in data and data["full"]

def test_preview_boost(sample_audio, tmp_path):
    data = client.post("/load", json={"audio_path": sample_audio}).json()
    out = str(tmp_path / "boost_api.mp4")
    r = client.post("/preview", json={"clean_path": data["clean_path"],
                                      "text": data["transcript"], "out_path": out, "boost": True})
    assert os.path.exists(r.json()["video_path"])

def test_cut_endpoint_shortens(sample_audio):
    data = client.post("/load", json={"audio_path": sample_audio}).json()
    before = data["duration"]
    r = client.post("/cut", json={"clean_path": data["clean_path"], "ranges": [[1.0, 3.0]]})
    after = r.json()
    assert after["duration"] < before
    assert after["clean_path"] != data["clean_path"]
