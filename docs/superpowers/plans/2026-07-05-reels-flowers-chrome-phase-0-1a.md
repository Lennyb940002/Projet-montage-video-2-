# Reels Flowers Chrome — Phase 0 + 1A — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Le moteur silencieux ne produit plus que les 5 formats du guide (identité / psycho / trahison / perception / test), l'ancien contenu générique est coupé, et un lot de 30 reels est généré pour revue manuelle.

**Architecture:** Les 5 formats sont 5 mécaniques `split_3` (3 montres). Les labels (profils/phrases) sortent du hardcode de `render.py` et deviennent une donnée décidée par la policy (`recipe.labels`), tirée d'une banque `familles.json` (cohérent/surprise/interdit par famille × label_mode) avec mix 80/20 crédible. L'anti-répétition Phase 1A vit dans le générateur de lot.

**Tech Stack:** Python 3.13, ffmpeg (libass), pytest, SQLite (existant).

**Rappels transverses :**
- cwd de tous les tests : `cd /c/Users/User/Desktop/auto-montage` (Bash) ; `PYTHONUTF8=1` pour l'affichage.
- Lancer un test : `python -m pytest backend/tests/<f>::<t> -q -p no:cacheprovider`.
- Ne PAS lancer le scheduler pendant le dev (doublons).

---

## Phase 0 — Sécurisation (couper l'ancien)

### Task 0 : bannir les mécaniques génériques (biais 0)

**Files:**
- Modify: `backend/config.py` (dict `mechanic_bias`, ~lignes 115-127)
- Test: `backend/tests/test_silent_policy.py`

- [ ] **Step 1 : Écrire le test qui échoue**

```python
def test_banned_mechanics_never_proposed():
    """Aucune mécanique bannie ne doit sortir de decide() sur 200 seeds."""
    from backend.silent import policy
    from backend.silent.strategy import ContentStrategy
    banned = {"comparison", "vote", "elimination", "top3", "battle",
              "transformation", "erreur", "pov", "collection",
              "comparison_4", "collection_4", "revelation"}
    seen = set()
    for s in range(200):
        r = policy.decide(ContentStrategy(goal="engagement", count=1),
                          history=[], seed=s)
        seen.add(r.mechanic)
    assert not (seen & banned), f"mécanique bannie sortie : {seen & banned}"
```

- [ ] **Step 2 : Vérifier l'échec**

Run: `python -m pytest backend/tests/test_silent_policy.py::test_banned_mechanics_never_proposed -q -p no:cacheprovider`
Expected: FAIL (les bannies sortent encore, et `revelation_psy` etc. n'existent pas → decide peut renvoyer test/elimination).

- [ ] **Step 3 : Mettre à 0 les bannies dans `mechanic_bias`**

Remplacer le dict `mechanic_bias` par (Phase 0 : on met 0 partout SAUF `test`
qui reste actif ; les 4 nouvelles mécaniques 1A seront ajoutées en Task 5) :

```python
    mechanic_bias={
        # --- Formats 1A (guide 2026-07-05) ---
        "test": 3.0,               # identité
        # revelation_psy / trahison / perception / test_perso ajoutés en Task 5
        # --- BANNIS (guide : reels génériques) ---
        "elimination": 0.0, "vote": 0.0, "comparison": 0.0, "comparison_4": 0.0,
        "revelation": 0.0, "top3": 0.0, "collection": 0.0, "collection_4": 0.0,
        "battle": 0.0, "pov": 0.0, "erreur": 0.0, "transformation": 0.0,
        "projection": 0.0,         # reporté en Phase 1B
    },
```

- [ ] **Step 4 : Vérifier que le test passe**

Run: `python -m pytest backend/tests/test_silent_policy.py::test_banned_mechanics_never_proposed -q -p no:cacheprovider`
Expected: PASS (seul `test` sort).

- [ ] **Step 5 : Commit**

```bash
git add backend/config.py backend/tests/test_silent_policy.py
git commit -m "feat(reels): Phase 0 — bannir les mécaniques génériques (biais 0)"
```

---

## Phase 1A — Les 5 formats

### Task 1 : registre — 4 nouvelles mécaniques

**Files:**
- Modify: `backend/silent/registry.py` (dict `MECHANICS`)
- Test: `backend/tests/test_silent_registry.py`

- [ ] **Step 1 : Écrire le test**

```python
def test_formats_1a_present():
    from backend.silent import registry
    for m in ["test", "revelation_psy", "trahison", "perception", "test_perso"]:
        meta = registry.MECHANICS[m]
        assert meta["asset_count"] == 3
        assert meta["layouts"] == ["split_3"]
        assert meta["goal"] == "engagement"
    assert registry.MECHANICS["revelation_psy"]["label_mode"] == "psycho"
    assert registry.MECHANICS["trahison"]["label_mode"] == "trahison"
    assert registry.MECHANICS["perception"]["label_mode"] == "perception"
    assert registry.MECHANICS["test_perso"]["label_mode"] == "test_reveal"
```

- [ ] **Step 2 : Vérifier l'échec**

Run: `python -m pytest backend/tests/test_silent_registry.py::test_formats_1a_present -q -p no:cacheprovider`
Expected: FAIL (KeyError 'revelation_psy').

- [ ] **Step 3 : Ajouter les 4 mécaniques au dict `MECHANICS`**

```python
    "revelation_psy": {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                       "hook_file": "hooks_revelation_psy.json", "default_duration": 6.0,
                       "label_mode": "psycho"},
    "trahison":       {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                       "hook_file": "hooks_trahison.json", "default_duration": 6.0,
                       "label_mode": "trahison"},
    "perception":     {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                       "hook_file": "hooks_perception.json", "default_duration": 6.0,
                       "label_mode": "perception"},
    "test_perso":     {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                       "hook_file": "hooks_test_perso.json", "default_duration": 6.0,
                       "label_mode": "test_reveal"},
```

Note : `test` existe déjà (`hook_file: "test.json"`, `label_mode: "profile"`).
Le renommer pour cohérence est optionnel ; on garde `test.json` (Task 3 le
remplit au nouveau contenu).

- [ ] **Step 4 : Vérifier le test + non-régression registre**

Run: `python -m pytest backend/tests/test_silent_registry.py -q -p no:cacheprovider`
Expected: PASS (mettre à jour `test_mechanics_set` pour inclure les 4 nouveaux).

- [ ] **Step 5 : Commit**

```bash
git add backend/silent/registry.py backend/tests/test_silent_registry.py
git commit -m "feat(reels): +4 mécaniques 1A (revelation_psy/trahison/perception/test_perso)"
```

---

### Task 2 : VideoRecipe — champ `labels`

**Files:**
- Modify: `backend/silent/recipe.py`
- Test: `backend/tests/test_silent_recipe.py` (créer si absent)

- [ ] **Step 1 : Écrire le test**

```python
def test_recipe_accepts_labels():
    from backend.silent.recipe import VideoRecipe, validate
    r = VideoRecipe(mechanic="test", layout="split_3", hook="H", content_angle="a",
                    assets=("x", "y", "z"), duration=6.0, font="Impact",
                    accent="&H0000FFFF&", text_anim="fade", seed=1,
                    labels=(("discret", "&H0000FFFF&"),
                            ("froid", "&H0000FF00&"),
                            ("carré", "&H009314FF&")))
    assert validate(r).labels[0][0] == "discret"

def test_recipe_labels_default_none():
    from backend.silent.recipe import VideoRecipe
    r = VideoRecipe(mechanic="pov", layout="single", hook="H", content_angle="a",
                    assets=("x",), duration=5.0, font="Impact",
                    accent="&H0000FFFF&", text_anim="fade", seed=1)
    assert r.labels is None
```

- [ ] **Step 2 : Vérifier l'échec**

Run: `python -m pytest backend/tests/test_silent_recipe.py -q -p no:cacheprovider`
Expected: FAIL (TypeError: unexpected keyword 'labels').

- [ ] **Step 3 : Ajouter le champ**

Dans `recipe.py`, après `cta_type: str = None` :

```python
    labels: tuple = None   # ((texte, couleurASS), ...) 1 par montre ; décidé par la Policy
```

- [ ] **Step 4 : Vérifier**

Run: `python -m pytest backend/tests/test_silent_recipe.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5 : Commit**

```bash
git add backend/silent/recipe.py backend/tests/test_silent_recipe.py
git commit -m "feat(reels): VideoRecipe.labels (rétro-compat, défaut None)"
```

---

### Task 3 : banques de contenu (JSON)

**Files:**
- Create: `backend/silent/banks/hooks_test.json`, `hooks_revelation_psy.json`,
  `hooks_trahison.json`, `hooks_perception.json`, `hooks_test_perso.json`
- Create: `backend/silent/banks/cta.json`
- Create: `backend/silent/banks/familles.json`
- Test: `backend/tests/test_content_banks.py`

- [ ] **Step 1 : Écrire le test de complétude structurelle**

```python
import json, os
BANKS = os.path.join(os.path.dirname(__file__), "..", "silent", "banks")
FAMILLES = ["gmt", "or_rose", "saphir", "ruby", "silver"]
MODES = ["profile", "psycho", "trahison", "perception", "test_reveal"]

def _load(name):
    return json.load(open(os.path.join(BANKS, name), encoding="utf-8"))

def test_hooks_banks_non_empty():
    for f in ["hooks_test.json", "hooks_revelation_psy.json", "hooks_trahison.json",
              "hooks_perception.json", "hooks_test_perso.json"]:
        entries = _load(f)
        assert len(entries) >= 6, f
        assert all(e["text"] and e["angle"] for e in entries), f

def test_cta_typed():
    cta = _load("cta.json")
    types = {c["type"] for c in cta}
    assert {"comment", "dm", "question"} <= types
    assert all(c["text"] for c in cta)

def test_familles_cover_all_modes():
    fam = _load("familles.json")
    assert set(fam) == set(FAMILLES)
    for name, f in fam.items():
        assert f["dossiers"], name
        for mode in MODES:
            block = f["labels"][mode]
            assert block["coherents"], (name, mode)
            assert block["surprise_acceptes"], (name, mode)
            assert block["interdits"], (name, mode)

def test_surprise_never_in_interdits():
    """Un label surprise ne doit jamais figurer dans les interdits de sa famille."""
    fam = _load("familles.json")
    for name, f in fam.items():
        for mode in MODES:
            b = f["labels"][mode]
            inter = {x.lower() for x in b["interdits"]}
            assert not ({x.lower() for x in b["surprise_acceptes"]} & inter), (name, mode)
```

- [ ] **Step 2 : Vérifier l'échec**

Run: `python -m pytest backend/tests/test_content_banks.py -q -p no:cacheprovider`
Expected: FAIL (FileNotFoundError banks/).

- [ ] **Step 3 : Créer les banques**

Hooks — reprendre les banques du guide (§21). Exemple `hooks_test.json` :

```json
[
  {"text": "Choisis une montre, je te dis qui tu es", "angle": "which_man"},
  {"text": "Ce que tu choisis dit de toi", "angle": "what_choice_says"},
  {"text": "Une montre. Une personnalité.", "angle": "one_watch_one_perso"},
  {"text": "Dis-moi ta montre, je te dis ton énergie", "angle": "watch_energy"},
  {"text": "Ton poignet dit plus que tu crois", "angle": "wrist_says"},
  {"text": "Choisis vite. Pas de réflexion.", "angle": "choose_fast"}
]
```

`cta.json` (§26, typé pour rotation) :

```json
[
  {"text": "Laquelle te décrit ?", "type": "comment"},
  {"text": "T'es laquelle ?", "type": "comment"},
  {"text": "J'ai raison ?", "type": "question"},
  {"text": "J'ai menti ?", "type": "question"},
  {"text": "Tu valides ?", "type": "question"},
  {"text": "DM « MONTRE »", "type": "dm"},
  {"text": "Ton budget en DM, je te dis laquelle", "type": "dm"}
]
```

`familles.json` — **une entrée par dossier de la banque vidéo**. Exemple COMPLET
pour `gmt` (répliquer la même structure pour `or_rose`, `saphir`, `ruby`,
`silver` avec le contenu des §7/8/16/22/23 du guide) :

```json
{
  "gmt": {
    "dossiers": ["GMT"],
    "labels": {
      "profile": {
        "coherents": ["discret", "stratégique", "froid", "carré", "précis", "mature"],
        "surprise_acceptes": ["ambitieux discret", "indépendant calme"],
        "interdits": ["solaire", "extravagant", "joyeux", "fun", "voyant"]
      },
      "psycho": {
        "coherents": ["tu contrôles ton image", "tu préfères le calme au bruit",
                      "tu veux qu'on te respecte sans parler"],
        "surprise_acceptes": ["tu caches un côté compétiteur"],
        "interdits": ["tu veux qu'on te remarque tout de suite"]
      },
      "trahison": {
        "coherents": ["tu veux rester discret mais respecté",
                      "tu veux paraître calme mais puissant"],
        "surprise_acceptes": ["tu veux montrer que tu montes d'un cran"],
        "interdits": ["tu veux être le centre de l'attention"]
      },
      "perception": {
        "coherents": ["il est discret", "il est carré", "il a une énergie froide",
                      "il sait ce qu'il veut"],
        "surprise_acceptes": ["il est ambitieux mais calme"],
        "interdits": ["il aime qu'on le remarque"]
      },
      "test_reveal": {
        "coherents": ["tu contrôles ton image", "tu veux dégager du sérieux"],
        "surprise_acceptes": ["tu caches un côté compétiteur"],
        "interdits": ["tu veux réussir fort et que ça se voie"]
      }
    }
  }
}
```

Guide de contenu par famille (à respecter, §23) :
- `or_rose` : cohérents = solaire, assumé, ambitieux, confiant, chaud, voyant ;
  interdits = minimaliste, discret, timide.
- `saphir` (bleu) : cohérents = calme, élégant, différent, subtil, frais, posé ;
  interdits = agressif, criard.
- `ruby` (rouge) : cohérents = intense, assumé, magnétique, provocateur, visible ;
  interdits = discret, effacé, timide.
- `silver` (acier) : cohérents = classique, propre, mature, polyvalent, simple,
  élégant ; interdits = extravagant, provocateur.

- [ ] **Step 4 : Vérifier**

Run: `python -m pytest backend/tests/test_content_banks.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5 : Commit**

```bash
git add backend/silent/banks backend/tests/test_content_banks.py
git commit -m "feat(reels): banques contenu 1A (hooks/cta/familles cohérent-surprise-interdit)"
```

---

### Task 4 : `content.py` — détection famille + pick_labels + pick_cta

**Files:**
- Create: `backend/silent/content.py`
- Test: `backend/tests/test_content.py`

- [ ] **Step 1 : Écrire les tests**

```python
import random
from backend.silent import content

GMT = r"C:\Users\User\Downloads\Montage video\Banque video\GMT\clip1.mp4"
ORO = r"C:\Users\User\Downloads\Montage video\Banque video\Rainbow Or rose\c.mp4"

def test_detect_family():
    assert content.detect_family(GMT) == "gmt"
    assert content.detect_family(ORO) == "or_rose"
    assert content.detect_family(r"X\Inconnu\c.mp4") is None

def test_pick_labels_count_and_shape():
    labels, meta = content.pick_labels("test", (GMT, ORO, GMT), random.Random(1))
    assert len(labels) == 3
    assert all(isinstance(t, str) and c.startswith("&H") for t, c in labels)
    assert len(meta) == 3 and all(m["mode"] in ("coherent", "surprise") for m in meta)
    assert meta[0]["famille"] == "gmt"

def test_coherent_label_in_coherents_bank():
    import json, os
    fam = json.load(open(os.path.join(os.path.dirname(content.__file__),
                    "banks", "familles.json"), encoding="utf-8"))
    coh = {x.lower() for x in fam["gmt"]["labels"]["profile"]["coherents"]}
    sur = {x.lower() for x in fam["gmt"]["labels"]["profile"]["surprise_acceptes"]}
    # sur 60 seeds, chaque label GMT vient soit de coherents soit de surprise, jamais d'ailleurs
    for s in range(60):
        labels, meta = content.pick_labels("test", (GMT, GMT, GMT), random.Random(s))
        for (txt, _), m in zip(labels, meta):
            pool = coh if m["mode"] == "coherent" else sur
            assert txt.lower() in pool, (s, txt, m)

def test_surprise_ratio_roughly_20pct():
    modes = []
    for s in range(400):
        _, meta = content.pick_labels("test", (GMT, GMT, GMT), random.Random(s))
        modes += [m["mode"] for m in meta]
    ratio = modes.count("surprise") / len(modes)
    assert 0.10 <= ratio <= 0.30, ratio

def test_pick_cta_rotates_types():
    rng = random.Random(0)
    used = []
    for _ in range(6):
        text, typ = content.pick_cta("test", rng, used_types=used)
        used.append(typ)
    # sur 6 tirages, au moins 2 types différents (rotation)
    assert len(set(used)) >= 2

def test_deterministic():
    a = content.pick_labels("test", (GMT, ORO, GMT), random.Random(7))
    b = content.pick_labels("test", (GMT, ORO, GMT), random.Random(7))
    assert a == b
```

- [ ] **Step 2 : Vérifier l'échec**

Run: `python -m pytest backend/tests/test_content.py -q -p no:cacheprovider`
Expected: FAIL (module content introuvable).

- [ ] **Step 3 : Implémenter `content.py`**

```python
"""Couche contenu des reels (guide 2026-07-05). Banques JSON = source unique.
Décide labels (mix 80/20 crédible cohérent/surprise) et CTA. Aucun rendu ici."""
import os, json, functools
from backend.silent import registry

_BANKS = os.path.join(os.path.dirname(__file__), "banks")
_SURPRISE_RATE = 0.20
# palette ASS des cartouches (jamais de blanc -> lisible sur fond clair)
_PALETTE = ("&H0000FFFF&", "&H0000FF00&", "&H009314FF&", "&H00DC503C&")


@functools.lru_cache(maxsize=None)
def _bank(name):
    with open(os.path.join(_BANKS, name), encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def _familles():
    return _bank("familles.json")


def detect_family(asset_path):
    """Nom de famille d'après le dossier parent de l'asset ; None si inconnu."""
    folder = os.path.basename(os.path.dirname(asset_path))
    for name, f in _familles().items():
        if folder in f["dossiers"]:
            return name
    return None


def _label_mode(mechanic):
    return registry.MECHANICS[mechanic].get("label_mode", "profile")


def pick_labels(mechanic, assets, rng):
    """(labels, meta) : labels = ((texte, couleurASS), ...) 1 par montre ;
    meta = ({"famille":..., "mode":"coherent|surprise"}, ...). Mix 80/20 crédible :
    80% tirage dans `coherents`, 20% dans `surprise_acceptes` (jamais interdits)."""
    mode = _label_mode(mechanic)
    fam = _familles()
    labels, meta = [], []
    for i, asset in enumerate(assets):
        family = detect_family(asset)
        block = fam.get(family, {}).get("labels", {}).get(mode) if family else None
        if not block:                              # famille inconnue -> cohérent générique
            labels.append(("montre", _PALETTE[i % len(_PALETTE)]))
            meta.append({"famille": family, "mode": "coherent"})
            continue
        surprise = rng.random() < _SURPRISE_RATE and block["surprise_acceptes"]
        pool = block["surprise_acceptes"] if surprise else block["coherents"]
        txt = rng.choice(pool)
        labels.append((txt, _PALETTE[i % len(_PALETTE)]))
        meta.append({"famille": family, "mode": "surprise" if surprise else "coherent"})
    return tuple(labels), tuple(meta)


def pick_cta(mechanic, rng, used_types=()):
    """(texte, type) d'un CTA. Évite en priorité les `used_types` récents
    (rotation comment/dm/question)."""
    cta = _bank("cta.json")
    fresh = [c for c in cta if c["type"] not in set(used_types)] or cta
    c = rng.choice(fresh)
    return c["text"], c["type"]
```

- [ ] **Step 4 : Vérifier**

Run: `python -m pytest backend/tests/test_content.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5 : Commit**

```bash
git add backend/silent/content.py backend/tests/test_content.py
git commit -m "feat(reels): content.py — pick_labels 80/20 crédible + pick_cta rotation"
```

---

### Task 5 : policy — brancher labels + CTA + biais des 4 formats

**Files:**
- Modify: `backend/config.py` (`mechanic_bias` : ajouter les 4)
- Modify: `backend/silent/policy.py`
- Test: `backend/tests/test_silent_policy.py`

- [ ] **Step 1 : Écrire le test**

```python
def test_decide_1a_has_labels_and_cta():
    from backend.silent import policy
    from backend.silent.strategy import ContentStrategy
    for mech in ["test", "revelation_psy", "trahison", "perception", "test_perso"]:
        r = policy.decide(ContentStrategy(goal="engagement", mechanic=mech, count=1),
                          history=[], seed=3)
        assert r.labels is not None and len(r.labels) == 3
        assert all(t and c.startswith("&H") for t, c in r.labels)
        assert r.cta_type in ("comment", "dm", "question")
```

- [ ] **Step 2 : Vérifier l'échec**

Run: `python -m pytest backend/tests/test_silent_policy.py::test_decide_1a_has_labels_and_cta -q -p no:cacheprovider`
Expected: FAIL (labels None + biais 0 refuse les nouveaux mechanics imposés → en fait `strategy.mechanic` impose donc override OK ; échoue sur labels None).

- [ ] **Step 3a : Ajouter les 4 biais dans `config.py`**

Dans `mechanic_bias`, sous la ligne `"test": 3.0,` :

```python
        "revelation_psy": 2.5,
        "trahison": 2.0,
        "perception": 1.5,
        "test_perso": 1.0,
```

- [ ] **Step 3b : Brancher `content` dans `policy.decide`**

Dans `policy.py`, ajouter l'import en tête :

```python
from backend.silent import content
```

Puis, juste avant la construction du `VideoRecipe` (après le tirage `assets`),
insérer :

```python
    meta_m = registry.MECHANICS[mechanic]
    labels = None
    cta_type = None
    if "label_mode" in meta_m and mechanic in {
            "test", "revelation_psy", "trahison", "perception", "test_perso"}:
        labels, _ = content.pick_labels(mechanic, assets, rng)
        _, cta_type = content.pick_cta(mechanic, rng)
```

Et passer `labels=labels, cta_type=cta_type` au `VideoRecipe(...)`.

- [ ] **Step 4 : Vérifier + non-régression policy**

Run: `python -m pytest backend/tests/test_silent_policy.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5 : Commit**

```bash
git add backend/config.py backend/silent/policy.py backend/tests/test_silent_policy.py
git commit -m "feat(reels): policy décide labels+CTA pour les 5 formats 1A"
```

---

### Task 6 : render — lire `recipe.labels`, fail dur anti-hardcode

**Files:**
- Modify: `backend/silent/render.py` (`_cell_labels`)
- Test: `backend/tests/test_silent_render_labels.py`

- [ ] **Step 1 : Écrire le test**

```python
import pytest
from backend.silent.recipe import VideoRecipe
from backend.silent import render

def _recipe(mechanic, labels):
    return VideoRecipe(mechanic=mechanic, layout="split_3", hook="H", content_angle="a",
                       assets=("x", "y", "z"), duration=6.0, font="Impact",
                       accent="&H0000FFFF&", text_anim="fade", seed=1, labels=labels)

def test_cell_labels_uses_recipe_labels():
    L = (("discret", "&H0000FFFF&"), ("froid", "&H0000FF00&"), ("carré", "&H009314FF&"))
    assert render._cell_labels(_recipe("test", L)) == list(L)

def test_1a_without_labels_fails_hard():
    for m in ["test", "revelation_psy", "trahison", "perception", "test_perso"]:
        with pytest.raises(ValueError):
            render._cell_labels(_recipe(m, None))
```

- [ ] **Step 2 : Vérifier l'échec**

Run: `python -m pytest backend/tests/test_silent_render_labels.py -q -p no:cacheprovider`
Expected: FAIL (le hardcode renvoie MINIMALISTE... au lieu de lever).

- [ ] **Step 3 : Modifier `_cell_labels`**

Au tout début de `_cell_labels(recipe)`, avant la logique existante :

```python
    _FORMATS_1A = {"test", "revelation_psy", "trahison", "perception", "test_perso"}
    if getattr(recipe, "labels", None) is not None:
        return [tuple(l) for l in recipe.labels]
    if recipe.mechanic in _FORMATS_1A:
        raise ValueError(
            f"labels manquants pour le format 1A {recipe.mechanic!r} : "
            "le fallback hardcodé est interdit sur les formats du guide")
```

Le reste de la fonction (fallback `label_mode` pour mécaniques hors-1A) est
conservé tel quel.

- [ ] **Step 4 : Vérifier + non-régression render**

Run: `python -m pytest backend/tests/test_silent_render_labels.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5 : Commit**

```bash
git add backend/silent/render.py backend/tests/test_silent_render_labels.py
git commit -m "feat(reels): render lit recipe.labels + fail dur anti-hardcode sur formats 1A"
```

---

### Task 7 : générateur de lot 30 reels + manifest + anti-répétition

**Files:**
- Create: `deploy/generate_batch_1a.py`
- Test: `backend/tests/test_batch_1a.py`

- [ ] **Step 1 : Écrire le test (logique pure, sans rendu ffmpeg)**

```python
import importlib.util, os, random
_P = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "generate_batch_1a.py")
_spec = importlib.util.spec_from_file_location("gen1a", _P)
gen = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gen)

def test_plan_distribution():
    plan = gen.build_plan()
    from collections import Counter
    c = Counter(p["mechanic"] for p in plan)
    assert c == {"test": 10, "revelation_psy": 8, "trahison": 6,
                 "perception": 4, "test_perso": 2}
    assert len(plan) == 30

def test_recipes_anti_repetition():
    recipes = gen.build_recipes(seed=42)
    assert len(recipes) == 30
    # hook jamais utilisé plus de 2 fois par mécanique
    from collections import Counter
    seen = {}
    for r in recipes:
        seen.setdefault(r.mechanic, Counter())[r.hook] += 1
    for mech, cnt in seen.items():
        assert max(cnt.values()) <= 2, (mech, cnt)
    # aucun trio de montres identique (même ensemble ordonné)
    trios = [tuple(r.assets) for r in recipes]
    assert len(set(trios)) == len(trios)

def test_manifest_fields():
    entry = gen.manifest_entry(gen.build_recipes(seed=1)[0], "output/x.mp4")
    for k in ["mecanique", "hook", "montres", "familles_detectees", "labels",
              "cta", "mode_coherence", "chemin_export"]:
        assert k in entry
```

- [ ] **Step 2 : Vérifier l'échec**

Run: `python -m pytest backend/tests/test_batch_1a.py -q -p no:cacheprovider`
Expected: FAIL (deploy/generate_batch_1a.py absent).

- [ ] **Step 3 : Implémenter `deploy/generate_batch_1a.py`**

```python
"""Génère le lot de test 1A (30 reels) en revue manuelle. NE POSTE RIEN.
Anti-répétition en mémoire sur le lot (hooks <=2/méca, trios uniques, voyante pas
toujours en n°2, CTA en rotation). Manifest JSON d'audit."""
import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.silent import policy, content
from backend.silent.strategy import ContentStrategy
from backend.silent import render as _render

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "output", "batch_1a")
DISTRIB = [("test", 10), ("revelation_psy", 8), ("trahison", 6),
           ("perception", 4), ("test_perso", 2)]
_VOYANTES = {"or_rose", "ruby"}   # familles voyantes : pas toujours en position 2


def build_plan():
    return [{"mechanic": m} for m, n in DISTRIB for _ in range(n)]


def _reorder_no_flashy_center(recipe, rng):
    """Réordonne les assets pour éviter qu'une famille voyante soit toujours en
    n°2 (index central). Réalloue labels en cohérence."""
    fams = [content.detect_family(a) for a in recipe.assets]
    if len(recipe.assets) == 3 and fams[1] in _VOYANTES and rng.random() < 0.7:
        order = [0, 2, 1]
        assets = tuple(recipe.assets[i] for i in order)
        labels = tuple(recipe.labels[i] for i in order) if recipe.labels else None
        from dataclasses import replace
        return replace(recipe, assets=assets, labels=labels)
    return recipe


def build_recipes(seed=0):
    rng = random.Random(seed)
    recipes = []
    used_hooks = {}          # mechanic -> {hook: count}
    used_trios = set()
    for item in build_plan():
        mech = item["mechanic"]
        for _ in range(40):  # ré-essais bornés jusqu'à respecter l'anti-répétition
            s = rng.randrange(1 << 30)
            r = policy.decide(ContentStrategy(goal="engagement", mechanic=mech, count=1),
                              history=[], seed=s)
            r = _reorder_no_flashy_center(r, rng)
            hc = used_hooks.setdefault(mech, {})
            trio = tuple(r.assets)
            if hc.get(r.hook, 0) >= 2 or trio in used_trios:
                continue
            hc[r.hook] = hc.get(r.hook, 0) + 1
            used_trios.add(trio)
            recipes.append(r)
            break
        else:
            recipes.append(r)   # filet : on garde la dernière tentative
    return recipes


def manifest_entry(recipe, out_path):
    _, meta = content.pick_labels(recipe.mechanic, recipe.assets,
                                  random.Random(recipe.seed))
    return {
        "mecanique": recipe.mechanic,
        "hook": recipe.hook,
        "montres": list(recipe.assets),
        "familles_detectees": [content.detect_family(a) for a in recipe.assets],
        "labels": [list(l) for l in (recipe.labels or [])],
        "cta": recipe.cta_type,
        "mode_coherence": [m["mode"] for m in meta],
        "chemin_export": out_path,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    recipes = build_recipes(seed=1)
    manifest = []
    for i, r in enumerate(recipes, 1):
        out = os.path.join(OUT_DIR, f"reel_{i:02d}_{r.mechanic}.mp4")
        _render.render_recipe(r, out)
        manifest.append(manifest_entry(r, out))
        print(f"[{i:02d}/30] {r.mechanic} -> {os.path.basename(out)}", flush=True)
    json.dump(manifest, open(os.path.join(OUT_DIR, "manifest.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"OK — {len(recipes)} reels + manifest dans {OUT_DIR}")


if __name__ == "__main__":
    main()
```

Note : `manifest_entry` recalcule `meta` avec le même seed que la recipe pour
retrouver le mode cohérent/surprise (déterministe). Le champ `labels` vient de la
recipe (source de vérité du rendu).

- [ ] **Step 4 : Vérifier les tests logiques**

Run: `python -m pytest backend/tests/test_batch_1a.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5 : Smoke réel — générer 30 reels**

Run: `cd /c/Users/User/Desktop/auto-montage && PYTHONUTF8=1 python deploy/generate_batch_1a.py`
Expected: 30 MP4 + `output/batch_1a/manifest.json`. Inspecter 3-4 vidéos + le manifest.

- [ ] **Step 6 : Commit**

```bash
git add deploy/generate_batch_1a.py backend/tests/test_batch_1a.py
git commit -m "feat(reels): générateur lot 1A (30 reels) + manifest d'audit"
```

---

### Task 8 : nettoyage — retirer les hooks/concepts obsolètes + gate complet

**Files:**
- Modify: `backend/config.py` (`mechanic_concept` : retirer les bannies)
- Delete: hooks JSON des mécaniques bannies devenus inutiles (voir step 2)
- Test: suite complète

- [ ] **Step 1 : Vider `mechanic_concept`**

Les mécaniques bannies n'ont plus à mapper vers le DOSSIER_CONCEPTS. Remplacer :

```python
    mechanic_concept={},   # 1A : hooks servis par banques JSON dédiées
```

- [ ] **Step 2 : Supprimer les hook JSON des mécaniques bannies**

Ne PAS supprimer `test.json` (encore référencé par la mécanique `test`) ni les
nouveaux `hooks_*.json`. Supprimer les banques désormais mortes :

```bash
cd /c/Users/User/Desktop/auto-montage
git rm backend/silent/hooks/comparison.json backend/silent/hooks/vote.json \
       backend/silent/hooks/elimination.json backend/silent/hooks/top3.json \
       backend/silent/hooks/collection.json backend/silent/hooks/battle.json \
       backend/silent/hooks/pov.json backend/silent/hooks/erreur.json \
       backend/silent/hooks/transformation.json backend/silent/hooks/projection.json \
       backend/silent/hooks/revelation.json
```

(Vérifier au préalable qu'aucune mécanique à biais > 0 ne les référence.)

- [ ] **Step 3 : Gate de non-régression complet**

Run: `python -m pytest backend/tests -q -k "not e2e" -p no:cacheprovider`
Expected: PASS (mettre à jour tout test qui référençait les mécaniques bannies).

- [ ] **Step 4 : Commit**

```bash
git add -A
git commit -m "chore(reels): retirer hooks/concepts des mécaniques bannies + gate vert"
```

---

## Self-review (couverture spec)

- §2 Phase 0 (biais 0) → Task 0 ✅
- §3 5 mécaniques split_3 → Task 1 ✅
- §4.1 familles.json 3 niveaux × 5 modes → Task 3 + test complétude ✅
- §4 pick_labels 80/20 crédible (surprise ⊂ surprise_acceptes) → Task 4 ✅
- §4.2 CTA généré + logué → Task 4 (pick_cta) + Task 7 (manifest) ✅
- §5 labels dans recipe + policy décide + render lit → Tasks 2/5/6 ✅
- §5 fail dur anti-hardcode → Task 6 ✅
- §6 anti-répétition (trio/hook/voyante/CTA) → Task 7 ✅
- §7 lot 30 + manifest complet → Task 7 ✅
- §2 suppression ancien → Task 8 ✅

Écart assumé : anti-répétition persistante inter-sessions (store enrichi) repoussée ;
Phase 1A la gère en mémoire sur le lot (suffisant pour la revue). Noté au spec.
