import contextlib, pytest
from backend.pipeline import publish_ig

class FakeResp:
    def __init__(self, data): self._d = data
    def json(self): return self._d

def make_fake(seq):
    calls = {"i": 0}
    def fake(url, **kw):
        d = seq[calls["i"]]; calls["i"] += 1
        return FakeResp(d)
    return fake

@contextlib.contextmanager
def fake_url(video_path):
    yield "https://fake.trycloudflare.com/clip.mp4"

def test_publish_reel_happy(monkeypatch):
    monkeypatch.setattr(publish_ig.httpx, "post",
                        make_fake([{"id": "CONT1"}, {"id": "MEDIA1"}]))
    monkeypatch.setattr(publish_ig.httpx, "get",
                        make_fake([{"status_code": "FINISHED"}]))
    out = publish_ig.publish_reel("x.mp4", "cap", "TOK", "IGID",
                                  url_provider=fake_url, sleep=lambda s: None)
    assert out == "MEDIA1"

def test_status_error_raises(monkeypatch):
    monkeypatch.setattr(publish_ig.httpx, "post", make_fake([{"id": "CONT1"}]))
    monkeypatch.setattr(publish_ig.httpx, "get", make_fake([{"status_code": "ERROR"}]))
    with pytest.raises(RuntimeError):
        publish_ig.publish_reel("x.mp4", "cap", "TOK", "IGID",
                                url_provider=fake_url, sleep=lambda s: None)

def test_graph_error_message(monkeypatch):
    monkeypatch.setattr(publish_ig.httpx, "post",
                        make_fake([{"error": {"message": "Invalid token"}}]))
    with pytest.raises(RuntimeError, match="Invalid token"):
        publish_ig.create_container("IGID", "url", "cap", "TOK")
