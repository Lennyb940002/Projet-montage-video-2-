import urllib.request
from backend.pipeline import tunnel

def test_serve_dir_serves_file(tmp_path):
    f = tmp_path / "clip.mp4"
    f.write_bytes(b"hello-bytes")
    server, port = tunnel.serve_dir(str(tmp_path))
    try:
        data = urllib.request.urlopen(f"http://127.0.0.1:{port}/clip.mp4").read()
        assert data == b"hello-bytes"
    finally:
        server.shutdown()

def test_free_port_is_int():
    p = tunnel._free_port()
    assert isinstance(p, int) and p > 0
