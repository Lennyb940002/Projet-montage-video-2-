import backend.distribution.uploadpost as up


class _FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload
    def json(self):
        return self._p


def test_post_success(monkeypatch):
    captured = {}
    def fake_post(url, headers=None, data=None, files=None, timeout=None):
        captured["url"] = url; captured["headers"] = headers
        captured["data"] = data; captured["files"] = files
        return _FakeResp(200, {"success": True, "results": {"tiktok": "ok", "instagram": "ok"}})
    monkeypatch.setattr(up.httpx, "post", fake_post)
    r = up.post("C:/v.mp4", "ma caption", ["tiktok", "instagram"],
                user="monprofil", token="TKN", _open=lambda p: b"x")
    assert r["ok"] is True
    assert captured["headers"]["Authorization"] == "Apikey TKN"
    assert captured["url"].endswith("/api/upload")
    assert captured["data"]["user"] == "monprofil"
    assert captured["data"]["platform[]"] == ["tiktok", "instagram"]
    assert captured["data"]["title"] == "ma caption"


def test_post_api_error_is_non_blocking(monkeypatch):
    def fake_post(url, headers=None, data=None, files=None, timeout=None):
        return _FakeResp(400, {"success": False, "error": "no profile connected"})
    monkeypatch.setattr(up.httpx, "post", fake_post)
    r = up.post("C:/v.mp4", "c", ["tiktok"], user="x", token="T", _open=lambda p: b"x")
    assert r["ok"] is False and "no profile" in r["error"]


def test_post_missing_credentials_is_non_blocking():
    r = up.post("C:/v.mp4", "c", ["tiktok"], user="", token="", _open=lambda p: b"x")
    assert r["ok"] is False and "credential" in r["error"].lower()
