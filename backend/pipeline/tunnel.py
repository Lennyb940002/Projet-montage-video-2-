import os, socket, threading, subprocess, re, time, contextlib, urllib.request
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

CF_DIR = os.path.join(os.path.expanduser("~"), ".automontage", "bin")
CF_PATH = os.path.join(CF_DIR, "cloudflared.exe")
CF_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p

def serve_dir(directory):
    port = _free_port()
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port

def ensure_cloudflared():
    if os.path.exists(CF_PATH):
        return CF_PATH
    os.makedirs(CF_DIR, exist_ok=True)
    urllib.request.urlretrieve(CF_URL, CF_PATH)
    return CF_PATH

def _start_tunnel(port):
    cf = ensure_cloudflared()
    proc = subprocess.Popen([cf, "tunnel", "--url", f"http://127.0.0.1:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = None
    start = time.time()
    while time.time() - start < 30:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            continue
        m = re.search(r"https://[-\w]+\.trycloudflare\.com", line)
        if m:
            url = m.group(0); break
    if not url:
        proc.terminate()
        raise RuntimeError("Tunnel cloudflared non démarré")
    return proc, url

@contextlib.contextmanager
def public_url(video_path):
    directory = os.path.dirname(os.path.abspath(video_path))
    name = os.path.basename(video_path)
    server, port = serve_dir(directory)
    proc = None
    try:
        proc, base = _start_tunnel(port)
        yield f"{base}/{name}"
    finally:
        if proc:
            proc.terminate()
        server.shutdown()
