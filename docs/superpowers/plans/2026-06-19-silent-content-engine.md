# Silent Content Engine V1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a second pipeline that generates silent vertical MP4s (1080×1920, 3–8 s) from watch clips/images + on-screen text, driven by a pure decision-making Policy Engine.

**Architecture:** 3 strict layers — `ContentStrategy` (intent) → `Policy Engine` (sole decider: constraint solver + sequence stabilizer) → `VideoRecipe` (immutable IR) → `Renderer` (pure execution) → `Store` (SQLite history). Asset selection uses Option C: Policy emits constraints, a Sampler does the sampling, the Recipe binds the result immutably.

**Tech Stack:** Python 3.13, ffmpeg (Gyan build) via `backend.ffmpeg`, SQLite (stdlib `sqlite3`), pytest, FastAPI (existing server), Electron UI (existing).

**Spec:** `docs/superpowers/specs/2026-06-19-silent-content-engine-design.md`

---

## File Structure

```
backend/silent/
├── __init__.py
├── recipe.py      VideoRecipe (frozen dataclass) + validate()
├── registry.py    MECHANICS + LAYOUTS + mechanics_for_goal()
├── hooks.py       pick_hook() + load_hooks()
│   └── hooks/     comparison.json · vote.json · revelation.json
├── sampler.py     sample(constraint, rng, clips_dir) → asset paths (Option C mechanical step)
├── strategy.py    ContentStrategy (frozen) + validate
├── store.py       SQLite generated_videos + insert() + query_recent()
├── policy.py    ★ decide(strategy, history, seed) → VideoRecipe
└── render.py      render_recipe(recipe, out) → MP4 (split_2, reveal)

backend/config.py            (modify: add SILENT dict)
backend/server.py            (modify: add /silent/* endpoints)
frontend/{index.html,renderer.js,preload.js,styles.css}  (modify: silent mode UI)

backend/tests/
├── test_silent_recipe.py
├── test_silent_registry.py
├── test_silent_hooks.py
├── test_silent_sampler.py
├── test_silent_strategy.py
├── test_silent_store.py
├── test_silent_policy.py
├── test_silent_render.py
└── test_silent_server.py
```

---

## Phase 0 — Config + package skeleton

### Task 0: SILENT config + package init

**Files:**
- Modify: `backend/config.py` (append)
- Create: `backend/silent/__init__.py`

- [ ] **Step 1: Add SILENT config block**

Append to `backend/config.py`:

```python
# --- Silent Content Engine (V1) --------------------------------------------
SILENT = dict(
    width=1080, height=1920, fps=30,
    min_duration=3.0, max_duration=8.0,
    window_n=5,                 # sliding history window read by the Policy
    w_rep=0.30,                 # repetition bias weight
    w_pat=0.40,                 # ABAB pattern penalty weight
    temperature=0.7,            # softmax temperature (fixed in V1)
    base_score=1.0,
    reveal_blur_sigma=25,       # gblur sigma for the "reveal" layout
    reveal_at=2.0,              # when the de-blur starts (s)
    reveal_fade=0.6,            # de-blur fade duration (s)
    fonts=["Arial Black", "Impact"],
    accents=["&H0000FFFF&", "&H0000FF00&", "&H00FFFFFF&", "&H009314FF&"],
    text_anims=["fade", "pop"],
)
SILENT_DB = os.path.join(os.path.expanduser("~"), ".automontage", "silent.db")
```

- [ ] **Step 2: Create package init**

Create `backend/silent/__init__.py`:

```python
"""Silent Content Engine — pipeline de génération de vidéos sans voix-off.
Architecture : ContentStrategy -> Policy -> VideoRecipe (immuable) -> Renderer -> Store.
Le Policy est le SEUL système de décision (cf docs/superpowers/specs/2026-06-19-silent-content-engine-design.md).
"""
```

- [ ] **Step 3: Verify import**

Run: `python -c "from backend.config import SILENT; print(SILENT['window_n'])"`
Expected: `5`

- [ ] **Step 4: Commit**

```bash
git add backend/config.py backend/silent/__init__.py
git commit -m "feat(silent): config SILENT + package skeleton"
```

---

## Phase 1 — Core correctness (registry, recipe, store, policy)

### Task 1: Registry (mechanics + layouts)

**Files:**
- Create: `backend/silent/registry.py`
- Test: `backend/tests/test_silent_registry.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_silent_registry.py`:

```python
from backend.silent import registry


def test_mechanics_have_required_fields():
    for name, m in registry.MECHANICS.items():
        assert m["goal"] in ("engagement", "retention")
        assert isinstance(m["asset_count"], int) and m["asset_count"] >= 1
        assert m["layouts"] and all(l in registry.LAYOUTS for l in m["layouts"])
        assert m["hook_file"].endswith(".json")
        assert m["default_duration"] > 0


def test_v1_has_three_mechanics():
    assert set(registry.MECHANICS) == {"comparison", "vote", "revelation"}


def test_mechanics_for_goal_filters():
    assert set(registry.mechanics_for_goal("engagement")) == {"comparison", "vote"}
    assert registry.mechanics_for_goal("retention") == ["revelation"]
    assert registry.mechanics_for_goal("nope") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.silent.registry'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/silent/registry.py`:

```python
"""Registre data-driven des mécaniques et layouts (V1). Source unique des
contraintes ; aucune décision ici (cf invariant architectural global)."""

MECHANICS = {
    "comparison": {"goal": "engagement", "asset_count": 2,
                   "layouts": ["split_2"], "hook_file": "comparison.json",
                   "default_duration": 6.0},
    "vote":       {"goal": "engagement", "asset_count": 2,
                   "layouts": ["split_2"], "hook_file": "vote.json",
                   "default_duration": 6.0},
    "revelation": {"goal": "retention",  "asset_count": 1,
                   "layouts": ["reveal"], "hook_file": "revelation.json",
                   "default_duration": 5.0},
}

LAYOUTS = {
    "split_2": {"asset_count": 2},
    "reveal":  {"asset_count": 1},
}


def mechanics_for_goal(goal):
    """Liste des mécaniques dont le goal correspond. Vide si aucun (P1 géré en aval)."""
    return [name for name, m in MECHANICS.items() if m["goal"] == goal]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_registry.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/silent/registry.py backend/tests/test_silent_registry.py
git commit -m "feat(silent): registry mécaniques + layouts V1"
```

---

### Task 2: VideoRecipe (frozen) + validate

**Files:**
- Create: `backend/silent/recipe.py`
- Test: `backend/tests/test_silent_recipe.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_silent_recipe.py`:

```python
import dataclasses
import pytest
from backend.silent.recipe import VideoRecipe, validate


def _ok_recipe(**over):
    base = dict(mechanic="comparison", layout="split_2",
                hook="A ou B ?", content_angle="a_or_b",
                assets=("a.mp4", "b.mp4"), duration=6.0,
                font="Arial Black", accent="&H0000FFFF&",
                text_anim="pop", seed=42)
    base.update(over)
    return VideoRecipe(**base)


def test_recipe_is_immutable():
    r = _ok_recipe()
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.mechanic = "vote"


def test_validate_accepts_valid_recipe():
    validate(_ok_recipe())  # no raise


def test_validate_rejects_unknown_mechanic():
    with pytest.raises(ValueError, match="mechanic"):
        validate(_ok_recipe(mechanic="ghost"))


def test_validate_rejects_layout_not_allowed_for_mechanic():
    with pytest.raises(ValueError, match="layout"):
        validate(_ok_recipe(layout="reveal"))  # reveal not allowed for comparison


def test_validate_rejects_wrong_asset_count():
    with pytest.raises(ValueError, match="asset"):
        validate(_ok_recipe(assets=("only_one.mp4",)))


def test_validate_rejects_duration_out_of_range():
    with pytest.raises(ValueError, match="duration"):
        validate(_ok_recipe(duration=99.0))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_recipe.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.silent.recipe'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/silent/recipe.py`:

```python
"""VideoRecipe : IR de production immuable. Toute la chaîne converge ici.
`validate` applique les invariants I2/I3/R3 ; échec => ValueError (R1: pas de
fallback silencieux)."""
from dataclasses import dataclass
from backend.config import SILENT
from backend.silent import registry


@dataclass(frozen=True)
class VideoRecipe:
    mechanic: str
    layout: str
    hook: str
    content_angle: str
    assets: tuple        # tuple => immuable
    duration: float
    font: str
    accent: str          # couleur ASS, ex "&H0000FFFF&"
    text_anim: str       # "fade" | "pop"
    seed: int


def validate(recipe):
    """Vérifie tous les invariants structurels avant émission (R3)."""
    m = registry.MECHANICS.get(recipe.mechanic)
    if m is None:
        raise ValueError(f"unknown mechanic: {recipe.mechanic!r}")            # I2
    if recipe.layout not in m["layouts"]:
        raise ValueError(
            f"layout {recipe.layout!r} not allowed for mechanic "
            f"{recipe.mechanic!r} (allowed: {m['layouts']})")                  # I3
    if len(recipe.assets) != m["asset_count"]:
        raise ValueError(
            f"asset count {len(recipe.assets)} != required "
            f"{m['asset_count']} for {recipe.mechanic!r}")                     # I2
    if not (SILENT["min_duration"] <= recipe.duration <= SILENT["max_duration"]):
        raise ValueError(
            f"duration {recipe.duration} out of range "
            f"[{SILENT['min_duration']}, {SILENT['max_duration']}]")           # I2
    return recipe
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_recipe.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/silent/recipe.py backend/tests/test_silent_recipe.py
git commit -m "feat(silent): VideoRecipe immuable + validate (invariants I2/I3/R3)"
```

---

### Task 3: Store (SQLite history)

**Files:**
- Create: `backend/silent/store.py`
- Test: `backend/tests/test_silent_store.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_silent_store.py`:

```python
from backend.silent.store import Store
from backend.silent.recipe import VideoRecipe


def _recipe(mech, angle, layout, assets):
    return VideoRecipe(mechanic=mech, layout=layout, hook="h",
                       content_angle=angle, assets=assets, duration=6.0,
                       font="Arial Black", accent="&H0000FFFF&",
                       text_anim="pop", seed=1)


def test_insert_and_query_recent_order(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.insert(_recipe("comparison", "a_or_b", "split_2", ("a", "b")), status="preview")
    s.insert(_recipe("vote", "vote_cta", "split_2", ("c", "d")), status="preview")
    s.insert(_recipe("revelation", "wait_last", "reveal", ("e",)), status="exported")
    recent = s.query_recent(2)
    # Plus récent d'abord
    assert [e["mechanic"] for e in recent] == ["revelation", "vote"]
    # Granularité figée : 3 dimensions exactement
    assert set(recent[0]) == {"mechanic", "content_angle", "layout"}


def test_query_recent_empty_db_returns_empty(tmp_path):
    s = Store(str(tmp_path / "empty.db"))
    assert s.query_recent(5) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.silent.store'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/silent/store.py`:

```python
"""Persistance SQLite des vidéos générées. Source de l'historique (snapshot
read-only) lu par le Policy — T1/T2. Aucune décision ici."""
import os, json, sqlite3, datetime

_SCHEMA = """
CREATE TABLE IF NOT EXISTS generated_videos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    mechanic_type TEXT NOT NULL,
    content_angle TEXT NOT NULL,
    layout_type   TEXT NOT NULL,
    asset_ids     TEXT NOT NULL,
    duration      REAL NOT NULL,
    status        TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self):
        return sqlite3.connect(self.path)

    def insert(self, recipe, status):
        with self._conn() as c:
            c.execute(
                "INSERT INTO generated_videos(created_at, mechanic_type, "
                "content_angle, layout_type, asset_ids, duration, status) "
                "VALUES (?,?,?,?,?,?,?)",
                (datetime.datetime.now().isoformat(timespec="seconds"),
                 recipe.mechanic, recipe.content_angle, recipe.layout,
                 json.dumps(list(recipe.assets)), recipe.duration, status))

    def query_recent(self, n):
        """Les n dernières entrées (plus récent d'abord), projetées sur les 3
        dimensions de diversité {mechanic, content_angle, layout}."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT mechanic_type, content_angle, layout_type "
                "FROM generated_videos ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        return [{"mechanic": r[0], "content_angle": r[1], "layout": r[2]}
                for r in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_store.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/silent/store.py backend/tests/test_silent_store.py
git commit -m "feat(silent): store SQLite + query_recent (history 3D)"
```

---

### Task 4: Hooks subsystem

**Files:**
- Create: `backend/silent/hooks.py`
- Create: `backend/silent/hooks/comparison.json`, `vote.json`, `revelation.json`
- Test: `backend/tests/test_silent_hooks.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_silent_hooks.py`:

```python
import random
from backend.silent import hooks


def test_pick_hook_returns_text_and_angle():
    text, angle = hooks.pick_hook("comparison", random.Random(1))
    assert isinstance(text, str) and text
    assert isinstance(angle, str) and angle


def test_pick_hook_angle_in_file():
    entries = hooks.load_hooks("comparison")
    angles = {e["angle"] for e in entries}
    _, angle = hooks.pick_hook("comparison", random.Random(7))
    assert angle in angles


def test_pick_hook_reroll_varies():
    # Sur plusieurs seeds différents, on doit obtenir >1 hook distinct
    got = {hooks.pick_hook("comparison", random.Random(s))[0] for s in range(20)}
    assert len(got) > 1


def test_all_v1_mechanics_have_hook_files():
    for mech in ("comparison", "vote", "revelation"):
        assert hooks.load_hooks(mech), f"no hooks for {mech}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_hooks.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.silent.hooks'`

- [ ] **Step 3: Write hook JSON files**

Create `backend/silent/hooks/comparison.json`:

```json
[
  {"text": "Laquelle tu choisis ?", "angle": "which_choose"},
  {"text": "A ou B ?", "angle": "a_or_b"},
  {"text": "Une seule à garder", "angle": "keep_one"},
  {"text": "Gauche ou droite ?", "angle": "left_right"},
  {"text": "Ta préférée ?", "angle": "favorite"}
]
```

Create `backend/silent/hooks/vote.json`:

```json
[
  {"text": "Votez A ou B en commentaire", "angle": "vote_ab"},
  {"text": "Choisis ton camp", "angle": "pick_side"},
  {"text": "Team 1 ou Team 2 ?", "angle": "team"},
  {"text": "Commente ton choix", "angle": "comment_choice"}
]
```

Create `backend/silent/hooks/revelation.json`:

```json
[
  {"text": "Attends la fin", "angle": "wait_end"},
  {"text": "Regarde bien...", "angle": "watch_close"},
  {"text": "La voilà", "angle": "here_it_is"},
  {"text": "Surprise", "angle": "surprise"}
]
```

- [ ] **Step 4: Write hooks.py**

Create `backend/silent/hooks.py`:

```python
"""Sous-système hooks : couche d'engagement orthogonale (≠ mécanique, ≠ layout).
Un fichier JSON par mécanique ; chaque entrée porte son `angle` (analytics)."""
import os, json, functools
from backend.silent import registry

_HOOKS_DIR = os.path.join(os.path.dirname(__file__), "hooks")


@functools.lru_cache(maxsize=None)
def load_hooks(mechanic):
    """Liste [{text, angle}] pour une mécanique. Fail-fast si fichier manquant (R2)."""
    m = registry.MECHANICS.get(mechanic)
    if m is None:
        raise ValueError(f"unknown mechanic: {mechanic!r}")
    path = os.path.join(_HOOKS_DIR, m["hook_file"])
    if not os.path.isfile(path):
        raise FileNotFoundError(f"hook file missing for {mechanic!r}: {path}")
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    if not entries:
        raise ValueError(f"empty hook file for {mechanic!r}")
    return entries


def pick_hook(mechanic, rng):
    """Tire (text, angle) au hasard (seedé via `rng`)."""
    e = rng.choice(load_hooks(mechanic))
    return e["text"], e["angle"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_hooks.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/silent/hooks.py backend/silent/hooks/*.json backend/tests/test_silent_hooks.py
git commit -m "feat(silent): hooks subsystem + JSON banks (comparison/vote/revelation)"
```

---

### Task 5: Sampler (Option C mechanical asset selection)

**Files:**
- Create: `backend/silent/sampler.py`
- Test: `backend/tests/test_silent_sampler.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_silent_sampler.py`:

```python
import os, random
import pytest
from backend.silent import sampler


def _make_clips(d, n):
    paths = []
    for i in range(n):
        p = os.path.join(d, f"watch_{i:03d}.mp4")
        open(p, "wb").write(b"x")
        paths.append(p)
    return paths


def test_sample_returns_requested_count(tmp_path):
    _make_clips(str(tmp_path), 5)
    out = sampler.sample({"count": 2, "filters": {}}, random.Random(1), str(tmp_path))
    assert len(out) == 2
    assert all(os.path.isfile(p) for p in out)


def test_sample_no_duplicates(tmp_path):
    _make_clips(str(tmp_path), 4)
    out = sampler.sample({"count": 3, "filters": {}}, random.Random(2), str(tmp_path))
    assert len(set(out)) == 3


def test_sample_seed_reproducible(tmp_path):
    _make_clips(str(tmp_path), 6)
    a = sampler.sample({"count": 2, "filters": {}}, random.Random(42), str(tmp_path))
    b = sampler.sample({"count": 2, "filters": {}}, random.Random(42), str(tmp_path))
    assert a == b


def test_sample_raises_if_not_enough_clips(tmp_path):
    _make_clips(str(tmp_path), 1)
    with pytest.raises(ValueError, match="not enough"):
        sampler.sample({"count": 2, "filters": {}}, random.Random(1), str(tmp_path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_sampler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.silent.sampler'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/silent/sampler.py`:

```python
"""Sampler d'assets (Option C). Étape MÉCANIQUE : ne décide rien, réalise le
tirage demandé par les contraintes émises par le Policy. Seedé => reproductible.
V1 : filters ignorés (pas de tags) ; V2 les exploitera."""
import os, glob
from backend.config import DEFAULT_CLIPS_DIR

_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".png", ".jpg", ".jpeg", ".webp")


def _list_assets(clips_dir):
    out = []
    for p in sorted(glob.glob(os.path.join(clips_dir, "*"))):
        if os.path.splitext(p)[1].lower() in _EXTS:
            out.append(p)
    return out


def sample(constraint, rng, clips_dir=DEFAULT_CLIPS_DIR):
    """Tire `constraint['count']` assets distincts depuis la banque (seedé).
    Lève ValueError si la banque n'a pas assez d'assets (R1/R2)."""
    count = constraint["count"]
    pool = _list_assets(clips_dir)
    if len(pool) < count:
        raise ValueError(
            f"not enough clips in {clips_dir}: need {count}, found {len(pool)}")
    return rng.sample(pool, count)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_sampler.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/silent/sampler.py backend/tests/test_silent_sampler.py
git commit -m "feat(silent): asset sampler (Option C, seedé, fail-fast)"
```

---

### Task 6: ContentStrategy

**Files:**
- Create: `backend/silent/strategy.py`
- Test: `backend/tests/test_silent_strategy.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_silent_strategy.py`:

```python
import pytest
from backend.silent.strategy import ContentStrategy, validate_strategy


def test_valid_strategy():
    validate_strategy(ContentStrategy(goal="engagement", count=1))


def test_rejects_unknown_goal():
    with pytest.raises(ValueError, match="goal"):
        validate_strategy(ContentStrategy(goal="virality", count=1))


def test_rejects_count_zero():
    with pytest.raises(ValueError, match="count"):
        validate_strategy(ContentStrategy(goal="engagement", count=0))


def test_rejects_goal_with_no_mechanic():
    # 'retention' a une mécanique (revelation) -> ok ; on fabrique un goal vide
    with pytest.raises(ValueError, match="no mechanic"):
        validate_strategy(ContentStrategy(goal="nonsense", count=1))


def test_mechanic_override_must_match_goal():
    with pytest.raises(ValueError, match="mechanic"):
        # revelation est 'retention', incompatible avec goal 'engagement'
        validate_strategy(ContentStrategy(goal="engagement", count=1,
                                          mechanic="revelation"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_strategy.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `backend/silent/strategy.py`:

```python
"""ContentStrategy : couche INTENTION. Le Policy la lit sans jamais la muter (I4)."""
from dataclasses import dataclass
from backend.silent import registry

_GOALS = ("engagement", "retention")


@dataclass(frozen=True)
class ContentStrategy:
    goal: str
    count: int
    mechanic: str = None       # override optionnel
    assets: tuple = None       # assets imposés (pick manuel UI)


def validate_strategy(strategy):
    """Valide l'intention avant décision (P1, P3, R2)."""
    if strategy.goal not in _GOALS:
        raise ValueError(f"unknown goal: {strategy.goal!r} (expected {_GOALS})")
    if strategy.count < 1:
        raise ValueError(f"count must be >= 1, got {strategy.count}")
    candidates = registry.mechanics_for_goal(strategy.goal)
    if not candidates:
        raise ValueError(f"no mechanic maps to goal {strategy.goal!r}")        # P1
    if strategy.mechanic is not None and strategy.mechanic not in candidates:
        raise ValueError(
            f"mechanic {strategy.mechanic!r} not valid for goal "
            f"{strategy.goal!r} (candidates: {candidates})")                    # I4/P2
    return strategy
```

Note: `test_rejects_goal_with_no_mechanic` uses goal `"nonsense"` which fails the `_GOALS` check first with message containing "goal"; adjust the test expectation — it raises on goal before "no mechanic". Update that test to assert `match="goal"`:

```python
def test_rejects_goal_with_no_mechanic():
    with pytest.raises(ValueError, match="goal"):
        validate_strategy(ContentStrategy(goal="nonsense", count=1))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_strategy.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/silent/strategy.py backend/tests/test_silent_strategy.py
git commit -m "feat(silent): ContentStrategy + validation (P1/P3/I4)"
```

---

### Task 7: Policy Engine — weighted selection + fatigue

**Files:**
- Create: `backend/silent/policy.py`
- Test: `backend/tests/test_silent_policy.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_silent_policy.py`:

```python
import random
from collections import Counter
import pytest
from backend.silent import policy
from backend.silent.strategy import ContentStrategy
from backend.silent.recipe import VideoRecipe, validate


def _decide(strategy, history=None, seed=0):
    return policy.decide(strategy, history or [], seed=seed)


def test_decide_returns_valid_recipe():
    r = _decide(ContentStrategy(goal="engagement", count=1, assets=("a.mp4", "b.mp4")))
    assert isinstance(r, VideoRecipe)
    validate(r)                       # I2/I3/R3
    assert r.mechanic in ("comparison", "vote")


def test_decide_is_seed_reproducible():
    s = ContentStrategy(goal="engagement", count=1, assets=("a.mp4", "b.mp4"))
    assert _decide(s, seed=42) == _decide(s, seed=42)          # S3


def test_decide_respects_goal():
    r = _decide(ContentStrategy(goal="retention", count=1, assets=("x.mp4",)))
    assert r.mechanic == "revelation"                           # P1


def test_decide_honors_mechanic_override():
    r = _decide(ContentStrategy(goal="engagement", count=1,
                                mechanic="vote", assets=("a.mp4", "b.mp4")))
    assert r.mechanic == "vote"


def test_repetition_bias_reduces_recent_mechanic():
    # Historique saturé de 'comparison' -> sur de nombreux seeds, 'vote' domine.
    history = [{"mechanic": "comparison", "content_angle": "a_or_b",
                "layout": "split_2"}] * 5
    counts = Counter()
    for seed in range(60):
        r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                          assets=("a.mp4", "b.mp4")),
                          history, seed=seed)
        counts[r.mechanic] += 1
    assert counts["vote"] > counts["comparison"]                # D1/D3 (biais, pas interdit)
    assert counts["comparison"] > 0                             # jamais exclusion dure


def test_decide_uses_weighted_not_argmax():
    # Sans historique, sur 60 seeds, les 2 mécaniques engagement apparaissent.
    counts = Counter()
    for seed in range(60):
        r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                          assets=("a.mp4", "b.mp4")),
                          [], seed=seed)
        counts[r.mechanic] += 1
    assert counts["comparison"] > 0 and counts["vote"] > 0      # S1 (pas argmax)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_policy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.silent.policy'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/silent/policy.py`:

```python
"""Policy Engine — SEUL système de décision. Fonction pure :
    decide(strategy, history, seed) -> VideoRecipe (immuable)

Double rôle : constraint solver + stochastic sampler ET sequence stabilizer (D0).
Fatigue = soft scoring (S1/S2), jamais exclusion dure. Aucun effet de bord, aucune
métrique externe (V1). Les assets imposés viennent de `strategy.assets` (Option C :
contrainte forte) ; sinon le Sampler tire depuis la banque."""
import math
import random as _random
from backend.config import SILENT
from backend.silent import registry, hooks, sampler
from backend.silent.recipe import VideoRecipe, validate


def _occurrences(mechanic, window):
    return sum(1 for h in window if h["mechanic"] == mechanic)


def _is_short_cycle(mechanic, window):
    """1 si choisir `mechanic` prolongerait une alternance ABAB.
    window = historique récent (plus récent d'abord)."""
    if len(window) >= 2 and window[1]["mechanic"] == mechanic \
            and window[0]["mechanic"] != mechanic:
        return 1
    return 0


def _weighted_choice(scored, temperature, rng):
    """Softmax sur les scores -> tirage pondéré (S1/S2). `scored` = [(item, score)]."""
    items = [it for it, _ in scored]
    exps = [math.exp(s / temperature) for _, s in scored]
    total = sum(exps)
    weights = [e / total for e in exps]
    r = rng.random()
    cum = 0.0
    for it, w in zip(items, weights):
        cum += w
        if r <= cum:
            return it
    return items[-1]


def decide(strategy, history, seed):
    """Traduit une intention en VideoRecipe validé. Lève ValueError si état
    invalide (R1 : pas de fallback silencieux)."""
    rng = _random.Random(seed)

    candidates = registry.mechanics_for_goal(strategy.goal)
    if not candidates:
        raise ValueError(f"no mechanic for goal {strategy.goal!r}")            # P1
    if strategy.mechanic is not None:
        if strategy.mechanic not in candidates:
            raise ValueError(f"mechanic {strategy.mechanic!r} not in {candidates}")
        candidates = [strategy.mechanic]                                       # I4 read-only

    window = list(history)[:SILENT["window_n"]]   # plus récent d'abord (cf store)
    denom = max(1, len(window))
    scored = []
    for m in candidates:
        score = (SILENT["base_score"]
                 - SILENT["w_rep"] * _occurrences(m, window) / denom            # D1/D3
                 - SILENT["w_pat"] * _is_short_cycle(m, window))                # D2
        scored.append((m, score))
    mechanic = _weighted_choice(scored, SILENT["temperature"], rng)            # S1/S2/S3

    meta = registry.MECHANICS[mechanic]
    layout = rng.choice(meta["layouts"])                                       # I3
    hook, angle = hooks.pick_hook(mechanic, rng)                               # D4 orthogonal

    # Assets — Option C : Policy émet la contrainte, Sampler réalise le tirage.
    # strategy.assets (pick manuel UI) = contrainte forte ; sinon tirage en banque.
    constraint = {"count": meta["asset_count"], "filters": {}}
    if strategy.assets is not None:
        assets = tuple(strategy.assets)
        if len(assets) != meta["asset_count"]:
            raise ValueError(
                f"strategy.assets count {len(assets)} != {meta['asset_count']}")
    else:
        assets = tuple(sampler.sample(constraint, rng))

    duration = max(SILENT["min_duration"],
                   min(SILENT["max_duration"], meta["default_duration"]))
    recipe = VideoRecipe(
        mechanic=mechanic, layout=layout, hook=hook, content_angle=angle,
        assets=assets, duration=duration,
        font=rng.choice(SILENT["fonts"]), accent=rng.choice(SILENT["accents"]),
        text_anim=rng.choice(SILENT["text_anims"]), seed=seed)
    return validate(recipe)                                                    # R3
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_policy.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/silent/policy.py backend/tests/test_silent_policy.py
git commit -m "feat(silent): Policy Engine — weighted sampling + fatigue (D0-D4,S1-S3)"
```

---

### Task 7B: Policy invariants suite (filet de sécurité architectural)

Suite transverse qui assert les invariants sur **toutes** les mécaniques à la fois (complète, ne
duplique pas, les tests par module). À relancer en continu pendant tout le build.

**Files:**
- Create: `backend/tests/test_policy_invariants.py`

- [ ] **Step 1: Write the invariant suite**

Create `backend/tests/test_policy_invariants.py`:

```python
"""Filet de sécurité architectural — invariants transverses du Policy Engine.
Vérifie sur TOUTES les mécaniques que les contrats tiennent ensemble."""
import dataclasses
from collections import Counter
import pytest
from backend.silent import registry, hooks, policy
from backend.silent.strategy import ContentStrategy
from backend.silent.recipe import VideoRecipe, validate

_FAKE = {1: ("a.mp4",), 2: ("a.mp4", "b.mp4")}  # assets bidon par asset_count


def _strategy_for(mechanic):
    goal = registry.MECHANICS[mechanic]["goal"]
    n = registry.MECHANICS[mechanic]["asset_count"]
    return ContentStrategy(goal=goal, count=1, mechanic=mechanic, assets=_FAKE[n])


def test_I1_every_produced_recipe_is_immutable():
    for mech in registry.MECHANICS:
        r = policy.decide(_strategy_for(mech), [], seed=1)
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.mechanic = "x"


def test_I2_I3_every_produced_recipe_validates():
    for mech in registry.MECHANICS:
        for seed in range(10):
            r = policy.decide(_strategy_for(mech), [], seed=seed)
            validate(r)                                  # I2 + I3 + duration range


def test_layout_always_in_allowed_set():
    for mech in registry.MECHANICS:
        allowed = registry.MECHANICS[mech]["layouts"]
        for seed in range(10):
            r = policy.decide(_strategy_for(mech), [], seed=seed)
            assert r.layout in allowed                    # I3


def test_hooks_valid_for_all_mechanics():
    for mech in registry.MECHANICS:
        entries = hooks.load_hooks(mech)
        assert entries and all("text" in e and "angle" in e for e in entries)


def test_P1_every_goal_maps_to_mechanic():
    for goal in ("engagement", "retention"):
        assert registry.mechanics_for_goal(goal)


def test_S1_selection_is_weighted_not_argmax():
    # Sans contrainte de mécanique, les 2 mécaniques engagement apparaissent.
    counts = Counter()
    for seed in range(80):
        r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                          assets=("a.mp4", "b.mp4")), [], seed=seed)
        counts[r.mechanic] += 1
    assert counts["comparison"] > 0 and counts["vote"] > 0


def test_S3_seed_determinism_across_mechanics():
    for mech in registry.MECHANICS:
        s = _strategy_for(mech)
        assert policy.decide(s, [], seed=99) == policy.decide(s, [], seed=99)


def test_D1_D3_no_hard_exclusion_but_biased():
    # Historique saturé d'une mécanique : elle reste possible (pas d'exclusion dure)
    # mais minoritaire (biais).
    hist = [{"mechanic": "comparison", "content_angle": "a_or_b",
             "layout": "split_2"}] * 5
    counts = Counter()
    for seed in range(80):
        r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                          assets=("a.mp4", "b.mp4")), hist, seed=seed)
        counts[r.mechanic] += 1
    assert counts["comparison"] > 0                       # jamais 0 (soft)
    assert counts["vote"] > counts["comparison"]          # biais vers diversité
```

- [ ] **Step 2: Run the suite**

Run: `python -m pytest backend/tests/test_policy_invariants.py -v`
Expected: PASS (8 tests)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_policy_invariants.py
git commit -m "test(silent): suite d'invariants transverse (filet architectural)"
```

---

## Phase 2 — First end-to-end (COMPARAISON → split_2 → MP4)

### Task 8: Renderer — split_2 layout

**Files:**
- Create: `backend/silent/render.py`
- Test: `backend/tests/test_silent_render.py`
- Uses fixtures: `backend/tests/fixtures/sample_insert.png`, `sample_insert.mp4` (created in earlier work)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_silent_render.py`:

```python
import os
from backend.silent.render import render_recipe
from backend.silent.recipe import VideoRecipe
from backend import ffmpeg

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
IMG = os.path.join(FIX, "sample_insert.png")
VID = os.path.join(FIX, "sample_insert.mp4")


def test_render_split_2_produces_vertical_mp4(tmp_path):
    r = VideoRecipe(mechanic="comparison", layout="split_2",
                    hook="A ou B ?", content_angle="a_or_b",
                    assets=(IMG, VID), duration=5.0,
                    font="Arial Black", accent="&H0000FFFF&",
                    text_anim="pop", seed=1)
    out = str(tmp_path / "cmp.mp4")
    render_recipe(r, out)
    assert os.path.exists(out)
    probe = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", out])
    assert "1080,1920" in probe.stdout
    assert abs(ffmpeg.probe_duration(out) - 5.0) < 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.silent.render'`

- [ ] **Step 3: Write the renderer**

Create `backend/silent/render.py`:

```python
"""Renderer — EXÉCUTION PURE. Consomme un VideoRecipe gelé, ne décide rien.
Texte (overlay ASS) = dernier filtre => toujours par-dessus les visuels.
Layouts V1 : split_2, reveal."""
import os
from backend import ffmpeg
from backend.config import SILENT

_W, _H, _FPS = SILENT["width"], SILENT["height"], SILENT["fps"]
_IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")


def _is_image(path):
    return os.path.splitext(path)[1].lower() in _IMG_EXT


def _input_args(path, duration):
    """Args ffmpeg d'entrée selon image vs vidéo, calés sur `duration`."""
    if _is_image(path):
        return ["-loop", "1", "-t", f"{duration:.3f}", "-i", path]
    return ["-stream_loop", "-1", "-t", f"{duration:.3f}", "-i", path]


def _ass_time(sec):
    cs = int(round(max(0, sec) * 100)); h = cs // 360000; cs %= 360000
    m = cs // 6000; cs %= 6000; s = cs // 100; c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _write_ass(recipe, path, lines):
    """Écrit un ASS minimal. `lines` = [(text, alignment, margin_v)]."""
    anim = ("{\\fad(150,0)}" if recipe.text_anim == "fade"
            else "{\\fad(80,0)\\fscx70\\fscy70\\t(0,160,\\fscx100\\fscy100)}")
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {_W}
PlayResY: {_H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{recipe.font},90,{recipe.accent},&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,6,2,5,80,80,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = []
    end = _ass_time(recipe.duration)
    for text, align, mv in lines:
        body.append(
            f"Dialogue: 0,{_ass_time(0)},{end},Default,,0,0,{mv},,"
            f"{{\\an{align}}}{anim}{text.upper()}")
    open(path, "w", encoding="utf-8").write(header + "\n".join(body) + "\n")


def _render_split_2(recipe, out_path):
    a, b = recipe.assets
    d = recipe.duration
    ass_path = out_path + ".ass"
    # Hook centré (an5) + badges A (haut, an8) / B (bas, an2)
    _write_ass(recipe, ass_path, [
        (recipe.hook, 5, 0),
        ("A", 8, 80),
        ("B", 2, 80),
    ])
    cmd = [ffmpeg.FFMPEG, "-y"]
    cmd += _input_args(a, d)
    cmd += _input_args(b, d)
    half = _H // 2
    fc = (f"[0:v]scale={_W}:{half}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{half},setsar=1[top];"
          f"[1:v]scale={_W}:{half}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{half},setsar=1[bot];"
          f"[top][bot]vstack=inputs=2,fps={_FPS},format=yuv420p[stack];"
          f"[stack]ass={os.path.basename(ass_path)}[vout]")
    cmd += ["-filter_complex", fc, "-map", "[vout]", "-t", f"{d:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(_FPS),
            "-movflags", "+faststart", "-an", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=os.path.dirname(os.path.abspath(ass_path)))
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"silent split_2 render failed: {r.stderr[-400:]}")


def render_recipe(recipe, out_path):
    """Dispatch par layout. Étend ici pour ajouter des layouts (V1.1/V1.2)."""
    if recipe.layout == "split_2":
        return _render_split_2(recipe, out_path)
    if recipe.layout == "reveal":
        return _render_reveal(recipe, out_path)
    raise ValueError(f"unknown layout: {recipe.layout!r}")
```

Note: `_render_reveal` is added in Task 10. To keep this task green, add a temporary stub at the bottom of `render.py` that Task 10 replaces:

```python
def _render_reveal(recipe, out_path):
    raise NotImplementedError("reveal layout: implemented in Task 10")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_render.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add backend/silent/render.py backend/tests/test_silent_render.py
git commit -m "feat(silent): renderer split_2 (COMPARAISON/VOTE) -> MP4 1080x1920"
```

---

### Task 9: End-to-end COMPARAISON through the full chain

**Files:**
- Test: `backend/tests/test_silent_render.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_silent_render.py`:

```python
def test_end_to_end_comparison_strategy_to_mp4(tmp_path, monkeypatch):
    """ContentStrategy -> Policy -> Recipe -> Renderer -> Store, sur vrais assets."""
    import random
    from backend.silent.strategy import ContentStrategy, validate_strategy
    from backend.silent import policy
    from backend.silent.store import Store

    strat = ContentStrategy(goal="engagement", count=1, mechanic="comparison",
                            assets=(IMG, VID))
    validate_strategy(strat)
    recipe = policy.decide(strat, history=[], seed=7)
    assert recipe.mechanic == "comparison" and recipe.layout == "split_2"

    out = str(tmp_path / "e2e.mp4")
    render_recipe(recipe, out)
    assert os.path.exists(out)

    store = Store(str(tmp_path / "e2e.db"))
    store.insert(recipe, status="preview")
    recent = store.query_recent(1)
    assert recent[0]["mechanic"] == "comparison"
    assert recent[0]["content_angle"] == recipe.content_angle
```

- [ ] **Step 2: Run test to verify it fails (if any wiring gap) or passes**

Run: `python -m pytest backend/tests/test_silent_render.py::test_end_to_end_comparison_strategy_to_mp4 -v`
Expected: PASS (all pieces already exist; this is the integration guard)

- [ ] **Step 3: No new implementation needed**

If the test fails, fix the specific wiring error reported (do not add fallbacks — R1).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_silent_render.py
git commit -m "test(silent): end-to-end COMPARAISON strategy->policy->render->store"
```

---

## Phase 3 — VOTE + REVELATION

### Task 10: Renderer — reveal layout (REVELATION)

**Files:**
- Modify: `backend/silent/render.py` (replace the `_render_reveal` stub)
- Test: `backend/tests/test_silent_render.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_silent_render.py`:

```python
def test_render_reveal_produces_vertical_mp4(tmp_path):
    r = VideoRecipe(mechanic="revelation", layout="reveal",
                    hook="Attends la fin", content_angle="wait_end",
                    assets=(IMG,), duration=5.0,
                    font="Arial Black", accent="&H00FFFFFF&",
                    text_anim="fade", seed=3)
    out = str(tmp_path / "rev.mp4")
    render_recipe(r, out)
    assert os.path.exists(out)
    probe = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", out])
    assert "1080,1920" in probe.stdout
    assert abs(ffmpeg.probe_duration(out) - 5.0) < 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_render.py::test_render_reveal_produces_vertical_mp4 -v`
Expected: FAIL with `NotImplementedError: reveal layout`

- [ ] **Step 3: Replace the stub with the real implementation**

In `backend/silent/render.py`, replace the `_render_reveal` stub with:

```python
def _render_reveal(recipe, out_path):
    """1 asset plein écran ; couche floutée par-dessus qui se dissout (flou->net)
    sur [reveal_at, reveal_at+reveal_fade]. Texte hook en bas."""
    (asset,) = recipe.assets
    d = recipe.duration
    ass_path = out_path + ".ass"
    _write_ass(recipe, ass_path, [(recipe.hook, 2, 140)])
    sigma = SILENT["reveal_blur_sigma"]
    at = min(SILENT["reveal_at"], max(0.0, d - SILENT["reveal_fade"]))
    fade = SILENT["reveal_fade"]
    cmd = [ffmpeg.FFMPEG, "-y"] + _input_args(asset, d)
    fc = (f"[0:v]scale={_W}:{_H}:force_original_aspect_ratio=increase,"
          f"crop={_W}:{_H},setsar=1,fps={_FPS},format=yuv420p,split[sharp][toblur];"
          f"[toblur]gblur=sigma={sigma}[blurred];"
          f"[blurred]fade=t=out:st={at:.3f}:d={fade:.3f}:alpha=1[blurfade];"
          f"[sharp][blurfade]overlay=format=auto[revealed];"
          f"[revealed]ass={os.path.basename(ass_path)}[vout]")
    cmd += ["-filter_complex", fc, "-map", "[vout]", "-t", f"{d:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(_FPS),
            "-movflags", "+faststart", "-an", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=os.path.dirname(os.path.abspath(ass_path)))
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"silent reveal render failed: {r.stderr[-400:]}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_render.py -v`
Expected: PASS (all render tests)

- [ ] **Step 5: Commit**

```bash
git add backend/silent/render.py backend/tests/test_silent_render.py
git commit -m "feat(silent): renderer reveal layout (REVELATION, flou->net)"
```

---

### Task 11: VOTE + REVELATION end-to-end coverage

**Files:**
- Test: `backend/tests/test_silent_render.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_silent_render.py`:

```python
def test_vote_end_to_end(tmp_path):
    import random
    from backend.silent.strategy import ContentStrategy
    from backend.silent import policy
    strat = ContentStrategy(goal="engagement", count=1, mechanic="vote",
                            assets=(IMG, VID))
    recipe = policy.decide(strat, [], seed=11)
    assert recipe.mechanic == "vote" and recipe.layout == "split_2"
    out = str(tmp_path / "vote.mp4")
    render_recipe(recipe, out)
    assert os.path.exists(out) and abs(ffmpeg.probe_duration(out) - recipe.duration) < 0.5


def test_revelation_end_to_end(tmp_path):
    from backend.silent.strategy import ContentStrategy
    from backend.silent import policy
    strat = ContentStrategy(goal="retention", count=1, assets=(IMG,))
    recipe = policy.decide(strat, [], seed=5)
    assert recipe.mechanic == "revelation" and recipe.layout == "reveal"
    out = str(tmp_path / "rev2.mp4")
    render_recipe(recipe, out)
    assert os.path.exists(out) and abs(ffmpeg.probe_duration(out) - recipe.duration) < 0.5
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_render.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_silent_render.py
git commit -m "test(silent): VOTE + REVELATION end-to-end"
```

---

## Phase 4 — Wiring (server endpoints + UI mode)

### Task 12: Service + server endpoints

**Files:**
- Create: `backend/silent_service.py`
- Modify: `backend/server.py`
- Test: `backend/tests/test_silent_server.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_silent_server.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_silent_server.py -v`
Expected: FAIL with 404 / missing endpoint

- [ ] **Step 3: Write the service**

Create `backend/silent_service.py`:

```python
"""Orchestration HTTP du Silent Engine : strategy -> policy -> render -> store."""
import os, uuid, dataclasses
from backend.config import WORKDIR, SILENT_DB, SILENT
from backend.silent import registry, policy
from backend.silent.strategy import ContentStrategy, validate_strategy
from backend.silent.render import render_recipe
from backend.silent.store import Store

_store = Store(SILENT_DB)


def list_mechanics():
    return [{"name": n, "goal": m["goal"], "asset_count": m["asset_count"]}
            for n, m in registry.MECHANICS.items()]


def generate(goal, mechanic=None, assets=None, seed=0, out_path=None):
    strat = ContentStrategy(goal=goal, count=1, mechanic=mechanic,
                            assets=tuple(assets) if assets else None)
    validate_strategy(strat)
    history = _store.query_recent(SILENT["window_n"])
    recipe = policy.decide(strat, history, seed=seed)
    out = out_path or os.path.join(WORKDIR, "silent_" + uuid.uuid4().hex + ".mp4")
    render_recipe(recipe, out)
    _store.insert(recipe, status="preview")
    return {"video_path": out, "recipe": dataclasses.asdict(recipe)}
```

Note: import `SILENT` in the service:

```python
from backend.config import WORKDIR, SILENT_DB, SILENT
```

- [ ] **Step 4: Add endpoints to server.py**

In `backend/server.py`, add after the existing imports:

```python
from backend import silent_service
```

Add the request model near the other `BaseModel` classes:

```python
class SilentReq(BaseModel):
    goal: str
    mechanic: str | None = None
    assets: list[str] | None = None
    seed: int = 0
    out_path: str | None = None
```

Add the endpoints near the other routes:

```python
@app.get("/silent/mechanics")
def silent_mechanics():
    return silent_service.list_mechanics()

@app.post("/silent/generate")
def silent_generate(req: SilentReq):
    return silent_service.generate(req.goal, req.mechanic, req.assets,
                                   req.seed, req.out_path)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_silent_server.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/silent_service.py backend/server.py backend/tests/test_silent_server.py
git commit -m "feat(silent): service + /silent/mechanics + /silent/generate endpoints"
```

---

### Task 13: UI — silent mode toggle + panel

**Files:**
- Modify: `frontend/index.html`, `frontend/preload.js`, `frontend/renderer.js`, `frontend/styles.css`

- [ ] **Step 1: Add preload bridge**

In `frontend/preload.js`, add inside `exposeInMainWorld('api', {...})`:

```javascript
  silentMechanics: ()                                  => get('/silent/mechanics'),
  silentGenerate:  (goal, mechanic, assets, seed)      => post('/silent/generate', { goal, mechanic, assets, seed }),
```

- [ ] **Step 2: Add the mode toggle + panel to index.html**

In `frontend/index.html`, add right after the opening `<header class="top">` logo span:

```html
      <div class="modeswitch" role="tablist" aria-label="Mode">
        <button id="modeVoice" class="modebtn active">🎙 Voix-off</button>
        <button id="modeSilent" class="modebtn">🤫 Silencieux</button>
      </div>
```

Add a silent panel before `</main>` (sibling of `.center`):

```html
      <section id="silentPanel" class="silent-panel" style="display:none">
        <h2 class="silent-title">Génération silencieuse</h2>
        <label class="silent-row">Objectif
          <select id="silentGoal" class="sel">
            <option value="engagement">Engagement (commentaires)</option>
            <option value="retention">Rétention</option>
          </select>
        </label>
        <label class="silent-row">Mécanique
          <select id="silentMech" class="sel"><option value="">Auto (selon objectif)</option></select>
        </label>
        <div class="silent-assets" id="silentAssets">Glisse 1–2 clips/images ici</div>
        <button id="silentGenBtn" class="btn green">🎬 Générer la vidéo</button>
        <video id="silentPreview" controls style="display:none"></video>
        <p id="silentStatus" class="status"></p>
      </section>
```

- [ ] **Step 3: Add styles**

Append to `frontend/styles.css`:

```css
.modeswitch { display: inline-flex; gap: 2px; margin-left: var(--s4);
  padding: 3px; background: var(--surface-3); border: 1px solid var(--line);
  border-radius: var(--r-pill); }
.modebtn { font-family: var(--font-ui); font-size: 13px; font-weight: 500;
  color: var(--dim); background: transparent; border: 0; border-radius: var(--r-pill);
  padding: 6px 14px; cursor: pointer; }
.modebtn.active { color: var(--on-accent); background: var(--accent); }
.silent-panel { display: flex; flex-direction: column; gap: var(--s4);
  align-items: center; justify-content: center; padding: var(--s6);
  background: radial-gradient(720px 420px at 50% 36%, rgba(231,180,90,.06), transparent 70%), #08080b; }
.silent-title { font-family: var(--font-display); font-size: 20px; color: var(--text); }
.silent-row { display: flex; flex-direction: column; gap: 6px; font-size: 12px;
  color: var(--dim); width: 320px; }
.silent-assets { width: 320px; min-height: 90px; display: grid; place-items: center;
  border: 1.5px dashed var(--line-2); border-radius: var(--r-lg); color: var(--faint);
  font-size: 12.5px; text-align: center; padding: var(--s4); }
.silent-assets.drag { border-color: var(--accent); background: var(--accent-soft); }
#silentPreview { width: 240px; aspect-ratio: 9/16; background: #000;
  border-radius: var(--r-lg); border: 1px solid var(--line-2); }
```

- [ ] **Step 4: Add renderer logic**

Append to `frontend/renderer.js`:

```javascript
// ====== Mode silencieux ======
const modeVoice = document.getElementById('modeVoice');
const modeSilent = document.getElementById('modeSilent');
const silentPanel = document.getElementById('silentPanel');
const dropScene = document.getElementById('drop');
const silentGoal = document.getElementById('silentGoal');
const silentMech = document.getElementById('silentMech');
const silentAssets = document.getElementById('silentAssets');
const silentGenBtn = document.getElementById('silentGenBtn');
const silentPreview = document.getElementById('silentPreview');
const silentStatus = document.getElementById('silentStatus');
let silentAssetPaths = [];

function setMode(silent) {
  silentPanel.style.display = silent ? 'flex' : 'none';
  dropScene.style.display = silent ? 'none' : 'flex';
  modeSilent.classList.toggle('active', silent);
  modeVoice.classList.toggle('active', !silent);
}
modeVoice.addEventListener('click', () => setMode(false));
modeSilent.addEventListener('click', () => setMode(true));

(async function initSilentMechs() {
  try {
    const list = await window.api.silentMechanics();
    list.forEach(m => { const o = document.createElement('option');
      o.value = m.name; o.textContent = `${m.name} (${m.goal})`; silentMech.appendChild(o); });
  } catch (_) {}
})();

['dragenter','dragover'].forEach(e => silentAssets.addEventListener(e, ev => {
  ev.preventDefault(); silentAssets.classList.add('drag'); }));
['dragleave','drop'].forEach(e => silentAssets.addEventListener(e, ev => {
  ev.preventDefault(); silentAssets.classList.remove('drag'); }));
silentAssets.addEventListener('drop', ev => {
  ev.preventDefault();
  silentAssetPaths = Array.from(ev.dataTransfer.files || [])
    .map(f => window.api.getPath(f)).filter(Boolean);
  silentAssets.textContent = silentAssetPaths.length
    ? silentAssetPaths.map(p => p.split(/[\\/]/).pop()).join(' · ')
    : 'Glisse 1–2 clips/images ici';
});

silentGenBtn.addEventListener('click', async () => {
  silentStatus.textContent = 'Génération…';
  try {
    const seed = Math.floor(Math.random() * 1e9);
    const res = await window.api.silentGenerate(
      silentGoal.value, silentMech.value || null, silentAssetPaths, seed);
    if (res.error) throw new Error(res.error);
    silentPreview.src = 'file://' + res.video_path.replace(/\\/g, '/') + '?t=' + Date.now();
    silentPreview.style.display = 'block';
    silentPreview.play().catch(() => {});
    silentStatus.textContent = `Prêt — ${res.recipe.mechanic} / ${res.recipe.content_angle}`;
  } catch (e) { silentStatus.textContent = 'Erreur : ' + (e.message || e); }
});
```

- [ ] **Step 5: Verify JS syntax**

Run: `node -c frontend/renderer.js && node -c frontend/preload.js && echo OK`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/preload.js frontend/renderer.js frontend/styles.css
git commit -m "feat(silent): UI mode toggle + génération panel"
```

---

### Task 14: Full-suite regression gate

**Files:** none (verification)

- [ ] **Step 1: Run the complete test suite**

Run: `python -m pytest backend/tests/ -q`
Expected: all tests pass (existing 170 + new silent tests), 0 failures

- [ ] **Step 2: If green, commit a marker (optional)**

```bash
git commit --allow-empty -m "test(silent): full suite green — V1 complete"
```

---

## Self-Review (run after writing)

**Spec coverage:** ContentStrategy (T6) ✓ · Policy Engine invariants I/D/S/T/P/R (T7, T2) ✓ · VideoRecipe immutable (T2) ✓ · registry (T1) ✓ · hooks + angle (T4) ✓ · Option C assets: Policy constraint + Sampler + Recipe binding (T5, T7) ✓ · history granularity 3D (T3) ✓ · DB schema (T3) ✓ · render split_2 + reveal, ASS last (T8, T10) ✓ · 3 mechanics, 2 layouts (T1, T8, T10) ✓ · no ML/analytics/price/tags (absent by construction) ✓ · UI mode (T13) ✓.

**Sequence stabilizer (D0):** covered by Policy reading `query_recent` window + fatigue tests (T7). Diversity over sequence validated by `test_repetition_bias_reduces_recent_mechanic`.

**Phasing matches user order:** Phase 1 core (T1-T7) → Phase 2 COMPARAISON e2e (T8-T9) → Phase 3 VOTE/REVELATION (T10-T11) → Phase 4 wiring (T12-T13).

**Type consistency:** `VideoRecipe` fields identical across T2/T3/T7/T8. `decide(strategy, history, seed, assets_override=None)` signature consistent T7/T9/T11/T12. `query_recent(n)` returns `{mechanic, content_angle, layout}` used identically in T3/T7/T12. `sample(constraint, rng, clips_dir)` consistent T5/T7.

**Out of scope (deferred):** TOP3/COLLECTION/ELIMINATION/POV mechanics, top3/grid_4/single layouts, tags, price, analytics, learning — all V1.1+.
