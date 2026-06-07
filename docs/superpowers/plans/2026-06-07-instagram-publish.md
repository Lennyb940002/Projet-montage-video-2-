# Publication Instagram (full API, immédiate) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Publier la vidéo exportée en Reel sur Instagram via l'API Graph (immédiat), avec URL publique fournie par un tunnel cloudflared, identifiants stockés en local.

**Architecture:** `settings.py` (token+id), `tunnel.py` (serveur local + cloudflared), `publish_ig.py` (flux container→poll→publish via httpx), exposés par service/serveur, + panneau Réglages et bouton Publier dans l'UI.

**Tech Stack:** Python (httpx déjà installé), cloudflared (binaire), FastAPI, Electron/JS.

---

## File Structure
- `backend/settings.py` — **nouveau** : lire/écrire `~/.automontage/settings.json`.
- `backend/pipeline/tunnel.py` — **nouveau** : serveur HTTP local + tunnel cloudflared.
- `backend/pipeline/publish_ig.py` — **nouveau** : flux Graph API Reels.
- `backend/service.py` / `backend/server.py` — orchestration + endpoints.
- `frontend/` — panneau Réglages + bouton Publier (index.html, styles.css, renderer.js, preload.js).

---

## Task 1: settings.py (identifiants locaux)

**Files:** Create `backend/settings.py`, Test `backend/tests/test_settings.py`

- [ ] **Step 1: Test (échec)**
```python
# backend/tests/test_settings.py
from backend import settings

def test_roundtrip(tmp_path):
    p = str(tmp_path / "s.json")
    settings.save({"ig_token": "T123", "ig_user_id": "42"}, path=p)
    d = settings.load(path=p)
    assert d["ig_token"] == "T123" and d["ig_user_id"] == "42"

def test_load_missing_returns_empty(tmp_path):
    assert settings.load(path=str(tmp_path / "nope.json")) == {}

def test_save_merges(tmp_path):
    p = str(tmp_path / "s.json")
    settings.save({"ig_token": "T"}, path=p)
    settings.save({"ig_user_id": "9"}, path=p)
    d = settings.load(path=p)
    assert d["ig_token"] == "T" and d["ig_user_id"] == "9"
```

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_settings.py -v` → FAIL.

- [ ] **Step 3: Écrire `backend/settings.py`**
```python
import os, json

DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".automontage", "settings.json")

def load(path=DEFAULT_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save(data, path=DEFAULT_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cur = load(path)
    cur.update(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=2)
    return cur
```

- [ ] **Step 4: Lancer (succès)** — PASS (3).

- [ ] **Step 5: Commit**
```bash
git add backend/settings.py backend/tests/test_settings.py
git commit -m "feat(ig): local settings store (token + ig id)"
```

---

## Task 2: tunnel.py (serveur local + cloudflared)

**Files:** Create `backend/pipeline/tunnel.py`, Test `backend/tests/test_tunnel.py`

- [ ] **Step 1: Test (échec) — on teste le serveur local seulement (pas cloudflared)**
```python
# backend/tests/test_tunnel.py
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
```

- [ ] **Step 2: Lancer (échec)** — FAIL (import).

- [ ] **Step 3: Écrire `backend/pipeline/tunnel.py`**
```python
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
```

- [ ] **Step 4: Lancer (succès)** — `pytest backend/tests/test_tunnel.py -v` → PASS (2).

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/tunnel.py backend/tests/test_tunnel.py
git commit -m "feat(ig): local file server + cloudflared quick tunnel"
```

---

## Task 3: publish_ig.py (flux Graph API)

**Files:** Create `backend/pipeline/publish_ig.py`, Test `backend/tests/test_publish_ig.py`

- [ ] **Step 1: Test (échec) — httpx mocké + url_provider factice**
```python
# backend/tests/test_publish_ig.py
import contextlib, pytest
from backend.pipeline import publish_ig

class FakeResp:
    def __init__(self, data): self._d = data
    def json(self): return self._d

def make_fake(seq):
    """seq = liste de réponses (dicts) renvoyées dans l'ordre des appels."""
    calls = {"i": 0}
    def fake(url, **kw):
        d = seq[calls["i"]]; calls["i"] += 1
        return FakeResp(d)
    return fake

@contextlib.contextmanager
def fake_url(video_path):
    yield "https://fake.trycloudflare.com/clip.mp4"

def test_publish_reel_happy(monkeypatch):
    # container -> id ; status -> FINISHED ; publish -> id
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
```

- [ ] **Step 2: Lancer (échec)** — FAIL (import).

- [ ] **Step 3: Écrire `backend/pipeline/publish_ig.py`**
```python
import time
import httpx

GRAPH = "https://graph.facebook.com/v21.0"

def _err(j):
    return j.get("error", {}).get("message", str(j))

def create_container(ig_user_id, video_url, caption, token):
    r = httpx.post(f"{GRAPH}/{ig_user_id}/media",
                   data={"media_type": "REELS", "video_url": video_url,
                         "caption": caption, "access_token": token}, timeout=60)
    j = r.json()
    if "id" not in j:
        raise RuntimeError("Instagram: " + _err(j))
    return j["id"]

def container_status(creation_id, token):
    r = httpx.get(f"{GRAPH}/{creation_id}",
                  params={"fields": "status_code", "access_token": token}, timeout=30)
    return r.json().get("status_code")

def wait_ready(creation_id, token, timeout=180, interval=4, sleep=time.sleep):
    waited = 0
    while waited < timeout:
        st = container_status(creation_id, token)
        if st == "FINISHED":
            return
        if st == "ERROR":
            raise RuntimeError("Instagram: l'encodage de la vidéo a échoué")
        sleep(interval); waited += interval
    raise RuntimeError("Instagram: délai d'encodage dépassé")

def publish(ig_user_id, creation_id, token):
    r = httpx.post(f"{GRAPH}/{ig_user_id}/media_publish",
                   data={"creation_id": creation_id, "access_token": token}, timeout=60)
    j = r.json()
    if "id" not in j:
        raise RuntimeError("Instagram: " + _err(j))
    return j["id"]

def publish_reel(video_path, caption, token, ig_user_id, url_provider, sleep=time.sleep):
    with url_provider(video_path) as url:
        cid = create_container(ig_user_id, url, caption, token)
        wait_ready(cid, token, sleep=sleep)
        return publish(ig_user_id, cid, token)
```

- [ ] **Step 4: Lancer (succès)** — `pytest backend/tests/test_publish_ig.py -v` → PASS (3).

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/publish_ig.py backend/tests/test_publish_ig.py
git commit -m "feat(ig): Graph API reel publish flow (container/poll/publish)"
```

---

## Task 4: service + endpoints

**Files:** Modify `backend/service.py`, `backend/server.py`, Test `backend/tests/test_server.py`

- [ ] **Step 1: `service.py` — ajouter en haut**
```python
from backend import settings as settings_mod
from backend.pipeline import tunnel, publish_ig
```
et à la fin :
```python
def get_settings():
    s = settings_mod.load()
    return {"ig_user_id": s.get("ig_user_id", ""), "has_token": bool(s.get("ig_token"))}

def save_settings(ig_token, ig_user_id):
    settings_mod.save({"ig_token": ig_token, "ig_user_id": ig_user_id})
    return get_settings()

def publish_instagram(video_path, caption):
    s = settings_mod.load()
    token, uid = s.get("ig_token"), s.get("ig_user_id")
    if not token or not uid:
        raise RuntimeError("Configure ton token et ton IG ID dans Réglages d'abord.")
    media_id = publish_ig.publish_reel(video_path, caption, token, uid, tunnel.public_url)
    return {"id": media_id}
```

- [ ] **Step 2: `server.py` — modèles + endpoints**

Ajouter les modèles :
```python
class SettingsReq(BaseModel):
    ig_token: str
    ig_user_id: str

class PublishReq(BaseModel):
    video_path: str
    caption: str
```
Ajouter les endpoints :
```python
@app.get("/settings")
def get_settings_ep():
    return service.get_settings()

@app.post("/settings")
def save_settings_ep(req: SettingsReq):
    return service.save_settings(req.ig_token, req.ig_user_id)

@app.post("/publish/instagram")
def publish_ig_ep(req: PublishReq):
    return service.publish_instagram(req.video_path, req.caption)
```

- [ ] **Step 3: Test serveur — `backend/tests/test_server.py`**
```python
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
```

- [ ] **Step 4: Lancer** — `pytest backend/tests/test_server.py -k "settings or publish_requires" -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/service.py backend/server.py backend/tests/test_server.py
git commit -m "feat(ig): settings + publish endpoints"
```

---

## Task 5: UI — Réglages + bouton Publier

**Files:** Modify `frontend/preload.js`, `frontend/index.html`, `frontend/styles.css`, `frontend/renderer.js`

- [ ] **Step 1: preload — ajouter**
```javascript
  getSettings: ()                              => get('/settings'),
  saveSettings: (ig_token, ig_user_id)         => post('/settings', { ig_token, ig_user_id }),
  publishInstagram: (video_path, caption)      => post('/publish/instagram', { video_path, caption }),
```

- [ ] **Step 2: index.html — bouton Réglages (barre du haut) + bouton Publier + modale**

Dans `.right` de `.top`, avant `#genBtn` :
```html
        <button id="setBtn" class="btn">⚙ Réglages</button>
```
Après `#expBtn` :
```html
        <button id="igBtn" class="btn" disabled>📷 Publier Instagram</button>
```
Avant `</body>` :
```html
  <div id="setModal" class="modal" style="display:none">
    <div class="modalbox">
      <h3>Réglages Instagram</h3>
      <label>Token longue durée</label>
      <input id="setToken" type="password" placeholder="EAAB...">
      <label>IG Business Account ID</label>
      <input id="setIgId" type="text" placeholder="178414...">
      <div class="modalbtns">
        <button id="setSave" class="btn primary">Enregistrer</button>
        <button id="setClose" class="btn">Fermer</button>
      </div>
      <p id="setMsg" class="status"></p>
    </div>
  </div>
```

- [ ] **Step 3: styles.css — modale**
```css
.modal { position:fixed; inset:0; background:#000a; display:flex; align-items:center; justify-content:center; z-index:100; }
.modalbox { background:#1b1b1d; border:1px solid #333; border-radius:12px; padding:20px; width:420px; display:flex; flex-direction:column; gap:8px; }
.modalbox h3 { color:#e8e8ea; margin-bottom:6px; }
.modalbox label { font-size:12px; color:#9a9aa0; margin-top:6px; }
.modalbox input { background:#0f0f10; color:#e8e8ea; border:1px solid #333; border-radius:6px; padding:8px; }
.modalbtns { display:flex; gap:8px; margin-top:12px; }
```

- [ ] **Step 4: renderer.js — logique**

En haut (après les autres const) :
```javascript
const setBtn = document.getElementById('setBtn');
const igBtn = document.getElementById('igBtn');
const setModal = document.getElementById('setModal');
const setToken = document.getElementById('setToken');
const setIgId = document.getElementById('setIgId');
const setSave = document.getElementById('setSave');
const setClose = document.getElementById('setClose');
const setMsg = document.getElementById('setMsg');

let lastExport = null;  // chemin de la dernière vidéo exportée

setBtn.addEventListener('click', async () => {
  const s = await window.api.getSettings();
  setIgId.value = s.ig_user_id || '';
  setToken.value = '';
  setToken.placeholder = s.has_token ? '•••• (déjà enregistré)' : 'EAAB...';
  setMsg.textContent = '';
  setModal.style.display = 'flex';
});
setClose.addEventListener('click', () => { setModal.style.display = 'none'; });
setSave.addEventListener('click', async () => {
  await window.api.saveSettings(setToken.value, setIgId.value);
  setMsg.textContent = 'Enregistré ✓';
});

igBtn.addEventListener('click', async () => {
  if (!lastExport) { setStatus('Exporte la vidéo d\'abord.'); return; }
  setStatus('Publication Instagram… (tunnel → encodage → publication)');
  try {
    const r = await window.api.publishInstagram(lastExport, captionBox.value);
    if (r.error) throw new Error(r.error);
    setStatus('Publié sur Instagram ✅ (id ' + r.id + ')');
  } catch (e) { setStatus('Erreur Instagram : ' + (e.message || e)); }
});
```

Dans le handler `expBtn` (export), après `setStatus('Exporté : ' + res.video_path);`, ajouter :
```javascript
    lastExport = res.video_path;
    igBtn.disabled = false;
```

- [ ] **Step 5: Vérifier syntaxe**
Run: `cd frontend && for f in preload.js renderer.js; do node --check "$f"; done` — aucune erreur.

- [ ] **Step 6: Commit**
```bash
git add frontend/preload.js frontend/index.html frontend/styles.css frontend/renderer.js
git commit -m "feat(ig): settings modal + Publish to Instagram button"
```

---

## Task 6: Vérification finale

- [ ] **Step 1: Suite complète** — `pytest backend/tests/ -q` → tous PASS.
- [ ] **Step 2: Test manuel (après setup Meta)** — `npm start` : Réglages → coller token + IG ID → Enregistrer. Déposer audio → Générer → Exporter → **Publier Instagram** → suivre l'état jusqu'à « Publié ✅ ». Vérifier le Reel sur le compte.

---

## Self-Review
- **Couverture spec :** settings store (T1) · tunnel cloudflared + serveur local (T2) · flux container/poll/publish (T3) · endpoints settings+publish (T4) · UI réglages+bouton (T5) · erreurs token/encodage (T3,T4 tests) · tests hors-ligne mockés (T2,T3,T4). ✓
- **Types :** `publish_reel(video_path, caption, token, ig_user_id, url_provider, sleep)` ; `public_url(video_path)` context manager ; `settings.load/save(path=)` ; `service.publish_instagram(video_path, caption)` ; `window.api.publishInstagram` → `/publish/instagram`. Cohérent. ✓
- **Pas de placeholder.** ✓
- **Note :** la publication réelle dépend des identifiants Meta de l'utilisateur (testée manuellement) ; tout le reste est testé hors-ligne.
