# Audio « machine de guerre » — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Nettoyage des silences adaptatif (seuil = plancher de bruit du fichier + souffle conservé) et détection plus fine (quasi-doublons, mots peu sûrs relatifs, longues pauses), sans rien couper automatiquement côté détection.

**Architecture:** Améliore `audio_clean.py` (noise_floor + seuil adaptatif) et `detect.py` (fuzzy retakes + lowconf relatif + long_pauses). Petit ajout UI (`renderer.js`) pour afficher les pauses 🟡. Réglages dans `config.py`. Non-régression vérifiée par les tests existants.

**Tech Stack:** Python (ffmpeg astats, difflib), JS.

---

## Task 1: Config (silence adaptatif + détection)

**Files:** Modify `backend/config.py`

- [ ] **Step 1: Remplacer la ligne `SILENCE = ...` et ajouter `DETECT`**

Remplacer :
```python
SILENCE = dict(keep=0.10, threshold="-35dB")
```
par :
```python
SILENCE = dict(keep=0.12, margin_db=8, floor_min=-55, floor_max=-28)
DETECT = dict(fuzzy_ratio=0.82, pause_min=0.7)
```

- [ ] **Step 2: Commit**
```bash
git add backend/config.py
git commit -m "feat(audio): adaptive silence + detect config"
```

---

## Task 2: Nettoyage adaptatif (noise_floor + remove_silences)

**Files:** Modify `backend/pipeline/audio_clean.py`, Test `backend/tests/test_audio_clean.py`

- [ ] **Step 1: Ajouter le test (échec attendu)**
```python
# à ajouter dans backend/tests/test_audio_clean.py
from backend.pipeline.audio_clean import noise_floor

def test_noise_floor_plausible(sample_audio):
    nf = noise_floor(sample_audio)
    assert isinstance(nf, float)
    assert -95.0 < nf < -10.0
```

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_audio_clean.py::test_noise_floor_plausible -v` → FAIL (import).

- [ ] **Step 3: Réécrire `backend/pipeline/audio_clean.py`** (la fonction `remove_silences` + ajout `noise_floor` ; `cut_audio` inchangé)

Remplacer le haut du fichier et `remove_silences` :
```python
import re
from backend import ffmpeg
from backend.config import SILENCE

def noise_floor(audio_path):
    """Plancher de bruit (dB) du fichier via ffmpeg astats. Fallback -50 dB."""
    r = ffmpeg.run([ffmpeg.FFMPEG, "-i", audio_path, "-af", "astats", "-f", "null", "-"])
    vals = re.findall(r"Noise floor dB:\s*(-?[0-9.]+)", r.stderr)
    if vals:
        try:
            return float(vals[-1])
        except ValueError:
            pass
    return -50.0

def remove_silences(audio_path, out_path):
    """Resserre les silences avec un seuil ADAPTATIF (plancher de bruit + marge),
    borné dans une plage sûre, en conservant un souffle. Ne retire que ce qui est
    sous le seuil -> jamais de parole."""
    s = SILENCE
    thr = noise_floor(audio_path) + s["margin_db"]
    thr = min(s["floor_max"], max(s["floor_min"], thr))   # clamp [-55, -28]
    thr_str = f"{thr:.0f}dB"
    keep = s["keep"]
    sr = (f"silenceremove=start_periods=1:start_duration=0:start_threshold={thr_str}:"
          f"stop_periods=-1:stop_duration={keep}:stop_threshold={thr_str}:detection=rms")
    r = ffmpeg.run([ffmpeg.FFMPEG, "-y", "-i", audio_path, "-af", sr,
                    "-c:a", "libmp3lame", "-q:a", "2", out_path])
    if r.returncode != 0:
        raise RuntimeError(f"silenceremove a échoué: {r.stderr[-300:]}")
    return out_path
```
(Garder `cut_audio` tel quel, plus bas dans le fichier.)

- [ ] **Step 4: Lancer** — `pytest backend/tests/test_audio_clean.py -v` → PASS (noise_floor + l'ancien test `test_remove_silences_shortens` toujours vert = non-régression).

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/audio_clean.py backend/tests/test_audio_clean.py
git commit -m "feat(audio): adaptive silence threshold (per-file noise floor) + breath"
```

---

## Task 3: Détection fine (fuzzy retakes + lowconf relatif + pauses)

**Files:** Modify `backend/pipeline/detect.py`, Test `backend/tests/test_detect.py`

- [ ] **Step 1: Ajouter les tests (échec attendu)**
```python
# à ajouter dans backend/tests/test_detect.py
from backend.pipeline.detect import long_pauses

def test_find_retakes_fuzzy():
    # reprise quasi-identique (un mot diffère) sur un bloc long
    a = "je te présente la daytona rainbow or".split()
    b = "je te présente la daytona rainbow rose".split()
    txt = a + b + ["et", "voila"]
    words = [W(t, i*0.4, i*0.4+0.3) for i, t in enumerate(txt)]
    r = find_retakes(words)
    assert len(r) >= 1

def test_low_confidence_relative():
    words = [W("a", 0, .3, .95), W("b", .3, .6, .96), W("c", .6, .9, .2), W("d", .9, 1.2, .94)]
    lc = low_confidence(words)          # sans seuil -> relatif
    assert 2 in lc and 0 not in lc

def test_long_pauses():
    words = [W("a", 0, .4), W("b", .5, .9), W("c", 2.0, 2.4)]  # gros gap avant c
    p = long_pauses(words, min_gap=0.7)
    assert len(p) == 1 and abs(p[0]["start"] - 0.9) < 1e-6

def test_detect_has_pauses():
    words = [W("a", 0, .3, .9), W("b", 2.0, 2.3, .9)]
    d = detect(words)
    assert "pauses" in d and len(d["pauses"]) == 1
```
(Le helper `W(...)` et l'import `find_retakes, low_confidence, detect` existent déjà en haut du fichier de test.)

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_detect.py -k "fuzzy or relative or pauses" -v` → FAIL.

- [ ] **Step 3: Modifier `backend/pipeline/detect.py`**

En haut, ajouter l'import config et difflib :
```python
import re, difflib
from backend.config import DETECT
```
Dans `find_retakes`, remplacer la condition d'égalité par une similarité (exacte OU floue) :
```python
                if (norms[i:i+L] == norms[j:j+L] or
                        difflib.SequenceMatcher(a=norms[i:i+L], b=norms[j:j+L]).ratio() >= DETECT["fuzzy_ratio"]) \
                        and all(norms[i:i+L]):
                    best = (L, gap, j)
                    break
```
Remplacer `low_confidence` par une version relative + mots tronqués :
```python
def low_confidence(words, threshold=None):
    if not words:
        return []
    if threshold is None:
        mean = sum(w.prob for w in words) / len(words)
        threshold = max(0.35, min(0.55, mean - 0.2))
    out = {i for i, w in enumerate(words) if w.prob < threshold}
    # mots tronqués : prob basse ET durée anormalement courte
    for i, w in enumerate(words):
        if w.prob < 0.45 and (w.end - w.start) < 0.12:
            out.add(i)
    return sorted(out)
```
Ajouter `long_pauses` et inclure les pauses dans `detect` :
```python
def long_pauses(words, min_gap=None):
    g = DETECT["pause_min"] if min_gap is None else min_gap
    out = []
    for i in range(len(words) - 1):
        if words[i + 1].start - words[i].end >= g:
            out.append({"start": words[i].end, "end": words[i + 1].start})
    return out

def detect(words):
    return {"retakes": find_retakes(words),
            "lowconf": low_confidence(words),
            "pauses": long_pauses(words)}
```

- [ ] **Step 4: Lancer** — `pytest backend/tests/test_detect.py -v` → PASS (anciens tests `test_low_confidence` [seuil 0.5 explicite], `test_find_retakes_exact_repeat`, `test_detect_shape` toujours verts = non-régression).

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/detect.py backend/tests/test_detect.py
git commit -m "feat(detect): fuzzy retakes + relative low-conf + long pauses"
```

---

## Task 4: UI — afficher les pauses 🟡

**Files:** Modify `frontend/renderer.js`

- [ ] **Step 1: Ajouter `pauses` à l'état**

Remplacer la ligne `const state = { ... };` (ligne ~84) par :
```javascript
const state = { cleanPath: null, duration: 0, words: [], retakes: [], lowconf: [], peaks: [], sel: null, pauses: [] };
```

- [ ] **Step 2: Lire les pauses dans `setState`**

Dans `setState`, après `state.lowconf = res.detect.lowconf;`, ajouter :
```javascript
  state.pauses = res.detect.pauses || [];
```

- [ ] **Step 3: Ajouter les pauses comme zones 🟡 dans `buildRegions`**

À la fin de `buildRegions`, avant la fermeture `}`, ajouter :
```javascript
  (state.pauses || []).forEach(p => regions.push({ type: 'y', kind: 'pause', start: p.start, end: p.end, ref: p }));
```

- [ ] **Step 4: Gérer « Garder » sur une pause dans `keepRegion`**

Remplacer la fonction `keepRegion` par :
```javascript
function keepRegion(reg) {
  if (reg.kind === 'pause') state.pauses = state.pauses.filter(p => p !== reg.ref);
  else if (reg.type === 'y') state.retakes = state.retakes.filter(r => r !== reg.ref);
  else { const s = new Set(reg.idxs); state.lowconf = state.lowconf.filter(i => !s.has(i)); }
  buildRegions(); drawWave();
}
```

- [ ] **Step 5: Vérifier la syntaxe**
Run: `cd frontend && node --check renderer.js`
Expected: aucune erreur.

- [ ] **Step 6: Commit**
```bash
git add frontend/renderer.js
git commit -m "feat(detect): show long pauses as yellow zones in UI"
```

---

## Task 5: Vérification finale

- [ ] **Step 1: Suite complète** — `pytest backend/tests/ -q` → tous PASS (y compris non-régression silence/détection).
- [ ] **Step 2: Test manuel** — `npm start` : déposer un audio. Vérifier : nettoyage OK (pas de mot mangé, débit naturel), zones 🟡 reprises (y compris quasi-doublons) + longues pauses, 🔴 mots douteux. Tester Garder/Supprimer sur une pause.

---

## Self-Review
- **Couverture spec :** noise_floor + seuil adaptatif + souffle (T2) · fuzzy retakes (T3) · lowconf relatif + tronqués (T3) · long_pauses (T3) · pauses en UI (T4) · config réglable (T1) · non-régression (tests existants conservés). ✓
- **Types :** `noise_floor(path)->float` ; `remove_silences(audio_path,out_path)` inchangée en signature ; `low_confidence(words, threshold=None)` (rétro-compatible) ; `long_pauses(words,min_gap=None)` ; `detect(words)->{retakes,lowconf,pauses}` ; UI `state.pauses`, `reg.kind==='pause'`. Cohérent. ✓
- **Pas de placeholder.** ✓
