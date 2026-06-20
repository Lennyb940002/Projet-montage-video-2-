# Axe Distribution — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Générer 4 vidéos/jour, les faire valider sur Telegram (✅/❌/🔄, timeout 30 min → post auto), puis publier sur Instagram + TikTok via upload-post, le tout en continu et host-agnostic.

**Architecture:** Programme Python always-on. Scheduler (APScheduler) déclenche `orchestrator.run_slot()` aux 4 créneaux → Policy/render (Silent Engine existant) → caption SEO (Gemini, fallback template) → bot Telegram pour validation → upload-post pour publier. État en SQLite. Secrets dans `~/.automontage/settings.json` (hors git).

**Tech Stack:** Python 3.13, httpx (déjà utilisé), python-telegram-bot, APScheduler, ffmpeg (existant), SQLite (stdlib), Gemini REST API.

**Spec:** `docs/superpowers/specs/2026-06-20-distribution-axis-design.md`

---

## File Structure

```
backend/distribution/
├── __init__.py
├── uploadpost.py    post(video, caption, platforms, user, token) -> dict (non-bloquant)
├── caption_seo.py   build_caption(recipe, model_names) -> (caption, hashtags)
├── store.py         table distribution_posts (insert/update/query)
├── telegram_bot.py  send_for_approval + boutons + callbacks + timeout
├── orchestrator.py  run_slot() : generate -> caption -> approval -> post
└── scheduler.py     APScheduler : 4 créneaux -> run_slot()
deploy/
├── setup.sh         install Oracle/VM (ffmpeg, venv, systemd)
└── automontage-dist.service   unit systemd
backend/tests/
├── test_uploadpost.py · test_caption_seo.py · test_dist_store.py
├── test_orchestrator.py · test_scheduler.py
```

Secrets (settings.json) : `uploadpost_token`, `uploadpost_user`, `gemini_key`,
`telegram_bot_token`, `telegram_chat_id`.

---

## Phase 1 — upload-post adapter (validation : une vraie vidéo postée)

### Task 1: Package distribution + uploadpost.post()

**Files:**
- Create: `backend/distribution/__init__.py`
- Create: `backend/distribution/uploadpost.py`
- Test: `backend/tests/test_uploadpost.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_uploadpost.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_uploadpost.py -v`
Expected: FAIL (ModuleNotFoundError: backend.distribution.uploadpost)

- [ ] **Step 3: Write minimal implementation**

Create `backend/distribution/__init__.py`:

```python
"""Axe distribution : génération planifiée -> validation Telegram -> publication
(upload-post). Cf docs/superpowers/specs/2026-06-20-distribution-axis-design.md."""
```

Create `backend/distribution/uploadpost.py`:

```python
"""Adapter upload-post.com (publication IG + TikTok). Exécutif et NON BLOQUANT :
renvoie {ok: bool, ids|error} au lieu de lever (le scheduler ne doit jamais crash)."""
import httpx

API_URL = "https://api.upload-post.com/api/upload"


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def post(video_path, caption, platforms, user, token, _open=_read):
    """Publie la vidéo sur `platforms` (ex ["tiktok","instagram"]) via le profil
    `user`. Renvoie {ok, results} ou {ok:False, error}."""
    if not token or not user:
        return {"ok": False, "error": "missing credentials (token/user)"}
    try:
        data = {"user": user, "platform[]": list(platforms), "title": caption}
        files = {"video": ("video.mp4", _open(video_path), "video/mp4")}
        r = httpx.post(API_URL, headers={"Authorization": f"Apikey {token}"},
                       data=data, files=files, timeout=180)
        j = r.json()
        if r.status_code == 200 and j.get("success", True):
            return {"ok": True, "results": j.get("results", j)}
        return {"ok": False, "error": j.get("error", f"HTTP {r.status_code}: {j}")}
    except Exception as e:
        return {"ok": False, "error": f"upload-post exception: {e}"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_uploadpost.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/distribution/__init__.py backend/distribution/uploadpost.py backend/tests/test_uploadpost.py
git commit -m "feat(dist): adapter upload-post (non-bloquant)"
```

### Task 2: Vérification post réel (manuel, gated)

**Files:** none (verification). **Prérequis utilisateur :** sur le dashboard upload-post,
connecter Instagram + TikTok et créer un profil ; mettre son nom dans settings
(`uploadpost_user`). Token déjà stocké (`uploadpost_token`).

- [ ] **Step 1: Stocker le nom de profil**

Run (remplacer `<PROFIL>` par le nom du profil upload-post de l'utilisateur) :
```bash
python -c "from backend import settings; settings.save({'uploadpost_user':'<PROFIL>'})"
```

- [ ] **Step 2: Poster une vraie vidéo de test**

Run:
```bash
python -c "
from backend import settings; from backend.distribution import uploadpost
s=settings.load()
r=uploadpost.post(r'C:/Users/User/Desktop/silent_review/video_1.mp4',
  'Test AutoMontage', ['tiktok','instagram'], s['uploadpost_user'], s['uploadpost_token'])
print(r)"
```
Expected: `{'ok': True, ...}` et le post apparaît sur les comptes. Si `{'ok': False}`,
lire l'erreur (souvent : profil non connecté / plateforme non liée) — corriger côté dashboard.

- [ ] **Step 3: Commit (marqueur)**

```bash
git commit --allow-empty -m "test(dist): post réel upload-post validé"
```

---

## Phase 2 — Caption SEO (Gemini + fallback)

### Task 3: caption_seo.build_caption()

**Files:**
- Create: `backend/distribution/caption_seo.py`
- Test: `backend/tests/test_caption_seo.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_caption_seo.py`:

```python
import backend.distribution.caption_seo as cs


def test_fallback_when_no_key(monkeypatch):
    monkeypatch.setattr(cs, "_gemini_key", lambda: None)
    cap, tags = cs.build_caption(mechanic="comparison",
                                 model_names=["Seiko Daytona Or rose", "Seiko Daytona Saphir"],
                                 hook="Laquelle ?")
    assert isinstance(cap, str) and cap                     # caption non vide
    assert 1 <= len(tags) <= 2                              # 1-2 hashtags max
    assert all(t.startswith("#") for t in tags)


def test_gemini_path(monkeypatch):
    monkeypatch.setattr(cs, "_gemini_key", lambda: "KEY")
    def fake_call(prompt, key):
        return "Découvre la Seiko Daytona Or rose vs Saphir 🌊\n\n#montre #seiko"
    monkeypatch.setattr(cs, "_gemini_generate", fake_call)
    cap, tags = cs.build_caption(mechanic="comparison",
                                 model_names=["Seiko Daytona Or rose"], hook="A ou B ?")
    assert "Seiko" in cap
    assert tags == ["#montre", "#seiko"][:len(tags)] and len(tags) <= 2


def test_gemini_error_falls_back(monkeypatch):
    monkeypatch.setattr(cs, "_gemini_key", lambda: "KEY")
    def boom(prompt, key): raise RuntimeError("gemini down")
    monkeypatch.setattr(cs, "_gemini_generate", boom)
    cap, tags = cs.build_caption(mechanic="vote", model_names=["X"], hook="Vote")
    assert cap and 1 <= len(tags) <= 2                      # fallback, jamais crash
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_caption_seo.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

Create `backend/distribution/caption_seo.py`:

```python
"""Génère une caption SEO (FR) + 1-2 hashtags depuis les montres + la mécanique.
Gemini si clé dispo, sinon fallback template. JAMAIS bloquant."""
import re
import httpx
from backend import settings

GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              "gemini-2.0-flash:generateContent")


def _gemini_key():
    return settings.load().get("gemini_key") or None


def _gemini_generate(prompt, key):
    r = httpx.post(f"{GEMINI_URL}?key={key}",
                   json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
    j = r.json()
    return j["candidates"][0]["content"]["parts"][0]["text"]


def _prompt(mechanic, model_names, hook):
    montres = ", ".join(model_names)
    return (
        "Tu es expert SEO réseaux sociaux horlogers. Rédige en FRANÇAIS une "
        "description Instagram/TikTok optimisée SEO pour une vidéo de montres.\n"
        f"Mécanique: {mechanic}. Accroche à l'écran: \"{hook}\". Montres: {montres}.\n"
        "Contraintes: ton premium, intègre les noms exacts des montres et des "
        "mots-clés horlogers, 2-3 phrases max, puis EXACTEMENT 1 à 2 hashtags "
        "pertinents (pas plus). Termine par la ligne des hashtags.")


def _split_caption_hashtags(text):
    tags = re.findall(r"#\w+", text)[:2]
    body = re.sub(r"#\w+", "", text).strip()
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body, tags


def _fallback(mechanic, model_names, hook):
    montres = " vs ".join(model_names) if len(model_names) > 1 else (model_names[0] if model_names else "cette montre")
    body = f"{hook} {montres}. Dis-nous en commentaire 👇"
    return body, ["#montre", "#seiko"]


def build_caption(mechanic, model_names, hook):
    """Renvoie (caption:str, hashtags:list[str] de longueur 1-2)."""
    key = _gemini_key()
    if key:
        try:
            txt = _gemini_generate(_prompt(mechanic, model_names, hook), key)
            body, tags = _split_caption_hashtags(txt)
            if body and tags:
                return body, tags[:2]
        except Exception:
            pass
    return _fallback(mechanic, model_names, hook)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_caption_seo.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/distribution/caption_seo.py backend/tests/test_caption_seo.py
git commit -m "feat(dist): caption SEO Gemini + fallback template"
```

---

## Phase 3 — État (SQLite)

### Task 4: distribution store

**Files:**
- Create: `backend/distribution/store.py`
- Test: `backend/tests/test_dist_store.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_dist_store.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_dist_store.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

Create `backend/distribution/store.py`:

```python
"""Persistance des posts de distribution (SQLite). Statuts :
pending | posted | auto_posted | skipped | failed."""
import os, json, sqlite3, datetime

_SCHEMA = """
CREATE TABLE IF NOT EXISTS distribution_posts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    video_path    TEXT NOT NULL,
    mechanic      TEXT NOT NULL,
    content_angle TEXT NOT NULL,
    layout        TEXT NOT NULL,
    asset_ids     TEXT NOT NULL,
    caption       TEXT NOT NULL,
    status        TEXT NOT NULL,
    tg_message_id TEXT,
    decided_at    TEXT
);
"""


class DistStore:
    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        with self._c() as c:
            c.executescript(_SCHEMA)

    def _c(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def insert(self, video_path, mechanic, content_angle, layout, asset_ids, caption):
        with self._c() as c:
            cur = c.execute(
                "INSERT INTO distribution_posts(created_at, video_path, mechanic, "
                "content_angle, layout, asset_ids, caption, status) "
                "VALUES (?,?,?,?,?,?,?, 'pending')",
                (datetime.datetime.now().isoformat(timespec="seconds"), video_path,
                 mechanic, content_angle, layout, json.dumps(asset_ids), caption))
            return cur.lastrowid

    def update_status(self, pid, status, tg_message_id=None):
        with self._c() as c:
            c.execute("UPDATE distribution_posts SET status=?, decided_at=?, "
                      "tg_message_id=COALESCE(?, tg_message_id) WHERE id=?",
                      (status, datetime.datetime.now().isoformat(timespec="seconds"),
                       tg_message_id, pid))

    def get(self, pid):
        with self._c() as c:
            r = c.execute("SELECT * FROM distribution_posts WHERE id=?", (pid,)).fetchone()
            return dict(r) if r else None

    def query_pending(self):
        with self._c() as c:
            rows = c.execute(
                "SELECT * FROM distribution_posts WHERE status='pending' ORDER BY id").fetchall()
            return [dict(r) for r in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_dist_store.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/distribution/store.py backend/tests/test_dist_store.py
git commit -m "feat(dist): store SQLite distribution_posts"
```

---

## Phase 4 — Orchestrateur + bot Telegram (machine à états)

### Task 5: orchestrator.generate_for_slot()

**Files:**
- Create: `backend/distribution/orchestrator.py`
- Test: `backend/tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_orchestrator.py`:

```python
import backend.distribution.orchestrator as orch


def test_generate_for_slot_builds_recipe_caption_and_inserts(tmp_path, monkeypatch):
    # Mock render (pas de ffmpeg) + caption + store
    from backend.silent.recipe import VideoRecipe
    fake_recipe = VideoRecipe(mechanic="comparison", layout="split_2", hook="A ou B ?",
                              content_angle="a_or_b", assets=("C:/Rainbow Or rose/x.mp4",),
                              duration=5.0, font="Arial Black", accent="&H00FFFFFF&",
                              text_anim="pop", seed=1)
    monkeypatch.setattr(orch, "_decide_recipe", lambda goal, seed: fake_recipe)
    monkeypatch.setattr(orch, "_render", lambda recipe, out: out)   # ne rend pas
    monkeypatch.setattr(orch.caption_seo, "build_caption",
                        lambda **k: ("ma caption", ["#montre"]))
    store = orch.DistStore(str(tmp_path / "d.db"))
    res = orch.generate_for_slot(goal="engagement", seed=1, store=store,
                                 out_dir=str(tmp_path))
    assert res["pid"] > 0
    row = store.get(res["pid"])
    assert row["status"] == "pending" and row["caption"] == "ma caption"
    assert res["video_path"].endswith(".mp4")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_orchestrator.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

Create `backend/distribution/orchestrator.py`:

```python
"""Orchestration d'un créneau : décide une recipe -> rend -> caption -> insère
en DB (statut pending). Le post effectif est déclenché par le bot Telegram
(approbation) ou le timeout. NON BLOQUANT."""
import os, uuid
from backend.config import WORKDIR, SILENT, SILENT_DB
from backend.silent import policy as _policy
from backend.silent.strategy import ContentStrategy
from backend.silent.render import render_recipe
from backend.distribution import caption_seo
from backend.distribution.store import DistStore


def _decide_recipe(goal, seed):
    strat = ContentStrategy(goal=goal, count=1)
    return _policy.decide(strat, history=[], seed=seed)


def _render(recipe, out_path):
    return render_recipe(recipe, out_path)


def _model_names(recipe):
    models = SILENT.get("models") or {}
    out = []
    for a in recipe.assets:
        folder = os.path.basename(os.path.dirname(a))
        out.append((models.get(folder) or {}).get("name", folder))
    return out


def generate_for_slot(goal, seed, store=None, out_dir=None):
    """Produit une vidéo + caption pour un créneau, l'insère 'pending'.
    Renvoie {pid, video_path, caption}."""
    store = store or DistStore(SILENT_DB)
    out_dir = out_dir or WORKDIR
    recipe = _decide_recipe(goal, seed)
    out = os.path.join(out_dir, "dist_" + uuid.uuid4().hex + ".mp4")
    _render(recipe, out)
    caption, tags = caption_seo.build_caption(
        mechanic=recipe.mechanic, model_names=_model_names(recipe), hook=recipe.hook)
    full = caption + ("\n\n" + " ".join(tags) if tags else "")
    pid = store.insert(video_path=out, mechanic=recipe.mechanic,
                       content_angle=recipe.content_angle, layout=recipe.layout,
                       asset_ids=list(recipe.assets), caption=full)
    return {"pid": pid, "video_path": out, "caption": full}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_orchestrator.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add backend/distribution/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat(dist): orchestrator generate_for_slot (recipe+render+caption+store)"
```

### Task 6: telegram_bot — envoi + décision + post

**Files:**
- Create: `backend/distribution/telegram_bot.py`
- Modify: `backend/distribution/orchestrator.py` (ajout `decide_and_post`)
- Test: `backend/tests/test_orchestrator.py` (append)

- [ ] **Step 1: Write the failing test (machine à états du post)**

Append to `backend/tests/test_orchestrator.py`:

```python
def test_decide_and_post_approved(tmp_path, monkeypatch):
    store = orch.DistStore(str(tmp_path / "d.db"))
    pid = store.insert(video_path="v.mp4", mechanic="comparison", content_angle="a",
                       layout="split_2", asset_ids=["x"], caption="cap")
    posted = {}
    monkeypatch.setattr(orch, "_do_post",
                        lambda row: posted.setdefault("v", row["video_path"]) or {"ok": True})
    orch.decide_and_post(pid, "approve", store=store)
    assert store.get(pid)["status"] == "posted" and posted["v"] == "v.mp4"


def test_decide_and_post_skip(tmp_path, monkeypatch):
    store = orch.DistStore(str(tmp_path / "d.db"))
    pid = store.insert(video_path="v", mechanic="vote", content_angle="a",
                       layout="split_2", asset_ids=["x"], caption="c")
    monkeypatch.setattr(orch, "_do_post", lambda row: (_ for _ in ()).throw(AssertionError("must not post")))
    orch.decide_and_post(pid, "skip", store=store)
    assert store.get(pid)["status"] == "skipped"


def test_decide_and_post_timeout_auto(tmp_path, monkeypatch):
    store = orch.DistStore(str(tmp_path / "d.db"))
    pid = store.insert(video_path="v", mechanic="vote", content_angle="a",
                       layout="split_2", asset_ids=["x"], caption="c")
    monkeypatch.setattr(orch, "_do_post", lambda row: {"ok": True})
    orch.decide_and_post(pid, "timeout", store=store)
    assert store.get(pid)["status"] == "auto_posted"


def test_decide_and_post_failure_marks_failed(tmp_path, monkeypatch):
    store = orch.DistStore(str(tmp_path / "d.db"))
    pid = store.insert(video_path="v", mechanic="vote", content_angle="a",
                       layout="split_2", asset_ids=["x"], caption="c")
    monkeypatch.setattr(orch, "_do_post", lambda row: {"ok": False, "error": "boom"})
    orch.decide_and_post(pid, "approve", store=store)
    assert store.get(pid)["status"] == "failed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_orchestrator.py -v`
Expected: FAIL (decide_and_post not defined)

- [ ] **Step 3: Add decide_and_post + _do_post to orchestrator.py**

Append to `backend/distribution/orchestrator.py`:

```python
from backend import settings
from backend.distribution import uploadpost

# Décision -> statut final. 'approve'/'timeout' postent ; 'skip' non.
_POST_STATUS = {"approve": "posted", "timeout": "auto_posted"}


def _do_post(row):
    s = settings.load()
    return uploadpost.post(row["video_path"], row["caption"], ["tiktok", "instagram"],
                           user=s.get("uploadpost_user", ""),
                           token=s.get("uploadpost_token", ""))


def decide_and_post(pid, decision, store=None):
    """Applique la décision (approve|skip|timeout) : poste si besoin, met le
    statut. NON BLOQUANT : échec post -> statut 'failed'."""
    store = store or DistStore(SILENT_DB)
    row = store.get(pid)
    if not row or row["status"] != "pending":
        return
    if decision == "skip":
        store.update_status(pid, "skipped")
        return
    res = _do_post(row)
    if res.get("ok"):
        store.update_status(pid, _POST_STATUS.get(decision, "posted"))
    else:
        store.update_status(pid, "failed")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_orchestrator.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Write the Telegram bot (envoi + boutons + callbacks)**

Create `backend/distribution/telegram_bot.py`:

```python
"""Bot Telegram : envoie la vidéo pour validation (boutons ✅/❌/🔄), gère les
callbacks et le timeout 30 min. Long-polling (OK sur VM always-on)."""
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler
from backend import settings
from backend.distribution import orchestrator
from backend.config import SILENT

APPROVAL_TIMEOUT_S = 30 * 60

_BUTTONS = InlineKeyboardMarkup([[
    InlineKeyboardButton("✅ Publier", callback_data="approve"),
    InlineKeyboardButton("❌ Skip", callback_data="skip"),
    InlineKeyboardButton("🔄 Refaire", callback_data="regenerate"),
]])


def _cfg():
    s = settings.load()
    return s.get("telegram_bot_token"), s.get("telegram_chat_id")


async def send_for_approval(app, pid, video_path, caption):
    """Envoie la vidéo + boutons. Programme le timeout -> post auto."""
    _, chat_id = _cfg()
    with open(video_path, "rb") as f:
        msg = await app.bot.send_video(chat_id=chat_id, video=f,
                                       caption=caption[:1000], reply_markup=_BUTTONS)
    app.job_queue.run_once(_on_timeout, APPROVAL_TIMEOUT_S, data=pid, name=f"to_{pid}")
    return msg.message_id


async def _on_timeout(context):
    pid = context.job.data
    orchestrator.decide_and_post(pid, "timeout")


async def _on_callback(update, context):
    q = update.callback_query
    await q.answer()
    decision = q.data
    pid = _pid_from_message(q.message)
    # annule le timeout en attente
    for j in context.job_queue.get_jobs_by_name(f"to_{pid}"):
        j.schedule_removal()
    if decision == "regenerate":
        await q.edit_message_caption(caption="🔄 Nouvelle version en cours…")
        from backend.distribution.scheduler import run_slot   # évite import circulaire
        run_slot(context.application)
        return
    orchestrator.decide_and_post(pid, "approve" if decision == "approve" else "skip")
    await q.edit_message_caption(
        caption="✅ Publié" if decision == "approve" else "❌ Skippé")


def _pid_from_message(message):
    # le pid est encodé dans la légende technique (dernière ligne "#<pid>")
    import re
    m = re.search(r"#(\d+)\s*$", message.caption or "")
    return int(m.group(1)) if m else None


def build_app():
    token, _ = _cfg()
    app = Application.builder().token(token).build()
    app.add_handler(CallbackQueryHandler(_on_callback))
    return app
```

Note: `send_for_approval` doit ajouter `\n#<pid>` à la fin de la légende pour que
`_pid_from_message` retrouve le pid. Modifier la ligne `caption=caption[:1000]` en
`caption=(caption[:980] + f"\n#{pid}")`.

- [ ] **Step 6: Install dependency + verify import**

Run: `pip install python-telegram-bot[job-queue]`
Then: `python -c "import backend.distribution.telegram_bot as t; print('ok')"`
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add backend/distribution/telegram_bot.py backend/distribution/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat(dist): bot Telegram (envoi+boutons+timeout) + decide_and_post"
```

---

## Phase 5 — Scheduler + déploiement

### Task 7: scheduler (4 créneaux)

**Files:**
- Create: `backend/distribution/scheduler.py`
- Test: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_scheduler.py`:

```python
import backend.distribution.scheduler as sched


def test_slots_are_configured():
    # 4 créneaux quotidiens Europe/Paris
    assert sched.SLOTS == [9, 12, 18, 22]
    assert sched.TIMEZONE == "Europe/Paris"


def test_build_scheduler_registers_four_jobs(monkeypatch):
    monkeypatch.setattr(sched, "run_slot", lambda app=None: None)
    scheduler = sched.build_scheduler(app=None)
    assert len(scheduler.get_jobs()) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_scheduler.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

Create `backend/distribution/scheduler.py`:

```python
"""Scheduler des 4 créneaux quotidiens. Au déclenchement : génère une vidéo et
l'envoie sur Telegram pour validation."""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.distribution import orchestrator

SLOTS = [9, 12, 18, 22]
TIMEZONE = "Europe/Paris"
# Alterne le goal selon le créneau (3 engagement, 1 rétention le soir).
_GOAL_BY_SLOT = {9: "engagement", 12: "engagement", 18: "engagement", 22: "retention"}


def run_slot(app=None, hour=None, seed=None):
    """Génère une vidéo pour le créneau et l'envoie sur Telegram (si app fourni)."""
    import random
    goal = _GOAL_BY_SLOT.get(hour, "engagement")
    res = orchestrator.generate_for_slot(goal=goal,
                                         seed=seed if seed is not None else random.randrange(10**9))
    if app is not None:
        from backend.distribution.telegram_bot import send_for_approval
        asyncio.create_task(send_for_approval(app, res["pid"], res["video_path"], res["caption"]))
    return res


def build_scheduler(app):
    sch = AsyncIOScheduler(timezone=TIMEZONE)
    for h in SLOTS:
        sch.add_job(run_slot, CronTrigger(hour=h, minute=0, timezone=TIMEZONE),
                    kwargs={"app": app, "hour": h}, id=f"slot_{h}")
    return sch


def main():
    from backend.distribution.telegram_bot import build_app
    app = build_app()
    sch = build_scheduler(app)
    sch.start()
    app.run_polling()   # bloque ; le scheduler tourne en arrière-plan


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install apscheduler` then `python -m pytest backend/tests/test_scheduler.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/distribution/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat(dist): scheduler 4 créneaux + main (polling + cron)"
```

### Task 8: Déploiement Oracle Free (script + systemd)

**Files:**
- Create: `deploy/setup.sh`
- Create: `deploy/automontage-dist.service`
- Create: `requirements.txt`

- [ ] **Step 1: Geler les dépendances**

Create `requirements.txt`:

```
fastapi
uvicorn
httpx
faster-whisper
python-telegram-bot[job-queue]
apscheduler
```

- [ ] **Step 2: Créer le service systemd**

Create `deploy/automontage-dist.service`:

```ini
[Unit]
Description=AutoMontage Distribution (scheduler + Telegram bot)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/auto-montage
ExecStart=/home/ubuntu/auto-montage/.venv/bin/python -m backend.distribution.scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Créer le script d'install**

Create `deploy/setup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Oracle Cloud Always Free / Ubuntu 22.04 — installe et lance le service 24/7.
sudo apt-get update
sudo apt-get install -y ffmpeg python3-venv git
cd /home/ubuntu
[ -d auto-montage ] || git clone <REPO_URL> auto-montage
cd auto-montage
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# secrets : créer ~/.automontage/settings.json (token upload-post, user, gemini,
# telegram_bot_token, telegram_chat_id) AVANT de démarrer le service.
mkdir -p ~/.automontage
sudo cp deploy/automontage-dist.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now automontage-dist
echo "OK — logs: journalctl -u automontage-dist -f"
```

- [ ] **Step 4: Vérifier la syntaxe bash**

Run: `bash -n deploy/setup.sh && echo OK`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add deploy/setup.sh deploy/automontage-dist.service requirements.txt
git commit -m "feat(dist): déploiement Oracle Free (setup.sh + systemd + requirements)"
```

### Task 9: Gate régression complète

- [ ] **Step 1: Run full suite**

Run: `python -m pytest backend/tests/ -q`
Expected: tous verts (silent + distribution)

- [ ] **Step 2: Commit marqueur**

```bash
git commit --allow-empty -m "test(dist): suite complète verte — axe distribution V1"
```

---

## Self-Review

**Spec coverage :** upload-post (T1-2) ✓ · caption SEO Gemini+fallback (T3) ✓ · store statuts (T4) ✓ · orchestrator generate (T5) ✓ · machine à états approve/skip/timeout/failed (T6) ✓ · bot Telegram envoi+boutons+timeout (T6) ✓ · regenerate (T6, via run_slot) ✓ · scheduler 4 créneaux Paris (T7) ✓ · déploiement Oracle systemd (T8) ✓ · secrets settings ✓ · non-bloquant partout ✓.

**Placeholder scan :** `<PROFIL>` (T2) et `<REPO_URL>` (T8) sont des valeurs à renseigner par l'utilisateur au déploiement, pas des placeholders de code — explicitement documentés.

**Type consistency :** `DistStore` (insert/update_status/get/query_pending) cohérent T4↔T5↔T6. `uploadpost.post(video, caption, platforms, user, token)` cohérent T1↔T6. `decide_and_post(pid, decision, store)` cohérent T6↔T7. `generate_for_slot(goal, seed, store, out_dir)` cohérent T5↔T7. `build_caption(mechanic, model_names, hook)` cohérent T3↔T5.

**Hors V1 (différé) :** retry auto, analytics, multi-comptes, tournoi.
