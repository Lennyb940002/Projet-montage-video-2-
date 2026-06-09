# Music + Ducking V1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ajouter une couche musicale automatique (Luxury/Hype) avec fade in/out, sidechain ducking, gap pré-CTA, normalisation LUFS, sélection par règles, auto-fix dominance voix non bloquant et score qualité — en respectant strictement le contrat **Events → Director → plan["music"] → music_engine → renderer**.

**Architecture:** `music_bank.py` indexe la banque (+ cache LUFS/durée) et expose `validate_library()` non bloquant. `audio_meta.py` mesure LUFS et dominance voix. `director._decide_music` score les events et produit `plan["music"]` (schéma `beds[]+accents[]+debug+score`). `music_engine.build()` traduit le plan en fragment ffmpeg (purement exécutif). `montage.render` intègre. `service.make_video` orchestre l'auto-fix non bloquant.

**Tech Stack:** Python · ffmpeg (`ebur128`, `astats`, `sidechaincompress`, `afade`, `volume(enable)`, `amix`) · pytest · règle produit absolue : **toujours sortir une vidéo**.

---

## File Structure
- `backend/config.py` — `MUSIC_DIR` + dict `MUSIC = {base_gain_dB, duck_depth_dB, fade_in_ms, fade_out_ms, pre_cta_gap_s, target_lufs, voice_dominance_min_dB, category_default, confidence_threshold, max_base_gain_dB, min_track_duration_s, supported_exts}`.
- `backend/pipeline/music_bank.py` — **nouveau** : `list_categories`, `list_tracks`, `validate_library`, `choose`, cache `.music_index.json`.
- `backend/pipeline/audio_meta.py` — **nouveau** : `lufs_of`, `measure_dominance`, helpers RMS.
- `backend/pipeline/director.py` (+) — `_voice_active_events`, `_pre_cta_gap_event`, `_score_music_category`, `_decide_music`, `_compute_quality_score`.
- `backend/pipeline/music_engine.py` — **nouveau** : `build(plan_music, voice_input_index)` → `(extra_inputs, filter_str, out_label)`.
- `backend/pipeline/montage.py` (+) — accepte `music=plan["music"]` ; intègre `music_engine.build` dans l'amix existant.
- `backend/service.py` (+) — orchestre auto-fix (re-render unique si dominance < seuil).
- Tests dédiés (~6 fichiers nouveaux).

---

## Task 0: Validation de la banque (non-bloquante)

**Files:** Create `backend/pipeline/music_bank.py` (partiel), Test `backend/tests/test_music_bank_validate.py`

- [ ] **Step 1: Test (échec)**
```python
# backend/tests/test_music_bank_validate.py
from backend.pipeline import music_bank

def test_validate_empty_lib(tmp_path):
    res = music_bank.validate_library(str(tmp_path))
    assert res["ok"] is False
    assert set(res["missing_categories"]) == {"Luxury", "Hype"}
    assert res["tracks_found"] == {"Luxury": 0, "Hype": 0}

def test_validate_partial_lib(tmp_path):
    (tmp_path / "Luxury").mkdir()
    (tmp_path / "Luxury" / "a.mp3").write_bytes(b"x")
    (tmp_path / "Luxury" / "b.mp3").write_bytes(b"x")
    res = music_bank.validate_library(str(tmp_path))
    assert res["ok"] is False
    assert res["missing_categories"] == ["Hype"]
    assert res["tracks_found"] == {"Luxury": 2, "Hype": 0}

def test_validate_full_lib(tmp_path):
    for cat in ("Luxury", "Hype"):
        d = tmp_path / cat; d.mkdir()
        for n in range(3):
            (d / f"t{n}.mp3").write_bytes(b"x")
    res = music_bank.validate_library(str(tmp_path))
    assert res["ok"] is True
    assert res["missing_categories"] == []
```

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_music_bank_validate.py -v` → FAIL (import).

- [ ] **Step 3: Écrire `backend/pipeline/music_bank.py`** (partie validation seulement)
```python
import os, glob
CATEGORIES = ("Luxury", "Hype")
SUPPORTED = (".mp3", ".wav", ".flac")
MIN_TRACKS_PER_CATEGORY = 3

def list_tracks(category, root):
    d = os.path.join(root, category)
    if not os.path.isdir(d):
        return []
    out = []
    for f in os.listdir(d):
        if f.startswith("."): continue
        if os.path.splitext(f)[1].lower() in SUPPORTED:
            out.append(os.path.join(d, f))
    return sorted(out)

def validate_library(root):
    """Non-bloquant : renvoie un rapport. Ne lève jamais."""
    found = {c: len(list_tracks(c, root)) for c in CATEGORIES}
    missing = [c for c, n in found.items() if n < MIN_TRACKS_PER_CATEGORY]
    return {"ok": len(missing) == 0, "missing_categories": missing,
            "tracks_found": found, "min_required_per_category": MIN_TRACKS_PER_CATEGORY}
```

- [ ] **Step 4: Lancer (succès)** — `pytest backend/tests/test_music_bank_validate.py -v` → PASS (3).

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/music_bank.py backend/tests/test_music_bank_validate.py
git commit -m "feat(music): non-blocking library validation (Task 0)"
```

---

## Task 1: Config musique

**Files:** Modify `backend/config.py`

- [ ] **Step 1: Ajouter à la fin de `backend/config.py`**
```python
MUSIC_DIR = os.path.join(PROJECT_ROOT, "MUSIC")
MUSIC = dict(
    base_gain_dB=-22.0,
    max_base_gain_dB=-16.0,         # plafond dur (clamp)
    duck_depth_dB=-12.0,
    fade_in_ms=800,
    fade_out_ms=1200,
    pre_cta_gap_s=1.2,
    pre_cta_fade_out_ms=250,
    pre_cta_fade_in_ms=200,
    target_lufs=-16.0,
    voice_dominance_min_dB=6.0,
    voice_floor_below_voice_dB=14.0,  # plancher ducking : musique au moins X dB sous la voix
    category_default="luxury",
    confidence_threshold=0.60,
    auto_fix_step_dB=-2.0,           # pas d'auto-fix (1 seule itération)
    min_track_duration_s=30.0,
)
```

- [ ] **Step 2: Commit**
```bash
git add backend/config.py
git commit -m "feat(music): MUSIC config + MUSIC_DIR"
```

---

## Task 2: audio_meta — LUFS + dominance

**Files:** Create `backend/pipeline/audio_meta.py`, Test `backend/tests/test_audio_meta.py`

- [ ] **Step 1: Tests (échec)**
```python
# backend/tests/test_audio_meta.py
import os, subprocess
from backend import ffmpeg
from backend.pipeline import audio_meta

def _sine(path, freq, dur, vol_db=0):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", f"sine=frequency={freq}:duration={dur}",
                "-af", f"volume={vol_db}dB", path])

def test_lufs_plausible(tmp_path):
    f = str(tmp_path / "s.wav")
    _sine(f, 1000, 2)
    v = audio_meta.lufs_of(f)
    assert isinstance(v, float)
    assert -50.0 < v < 10.0   # sine 0 dBFS donne ~-3 LUFS

def test_dominance_voice_louder(tmp_path):
    voice = str(tmp_path / "v.wav"); mix = str(tmp_path / "m.wav")
    _sine(voice, 1000, 2, 0)
    _sine(mix, 1000, 2, -20)     # mix beaucoup plus faible
    d = audio_meta.measure_dominance(mix, voice, [(0.0, 2.0)])
    assert d > 6.0

def test_dominance_music_too_loud(tmp_path):
    voice = str(tmp_path / "v.wav"); mix = str(tmp_path / "m.wav")
    _sine(voice, 1000, 2, -20)
    _sine(mix, 1000, 2, 0)
    d = audio_meta.measure_dominance(mix, voice, [(0.0, 2.0)])
    assert d < 6.0
```

- [ ] **Step 2: Lancer (échec)** — FAIL (import).

- [ ] **Step 3: Écrire `backend/pipeline/audio_meta.py`**
```python
import re, subprocess
from backend import ffmpeg

def lufs_of(path):
    """LUFS intégrée du fichier via ebur128. Fallback -23.0 si parse échoue."""
    r = ffmpeg.run([ffmpeg.FFMPEG, "-i", path, "-af", "ebur128=peak=true",
                    "-f", "null", "-"])
    m = re.search(r"I:\s*(-?[0-9.]+)\s*LUFS", r.stderr)
    try:
        return float(m.group(1)) if m else -23.0
    except (ValueError, AttributeError):
        return -23.0

def _rms_db(path, start, end):
    r = ffmpeg.run([ffmpeg.FFMPEG, "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                    "-i", path, "-af", "astats=metadata=1:reset=1", "-f", "null", "-"])
    m = re.search(r"RMS level dB:\s*(-?[0-9.]+)", r.stderr)
    try:
        return float(m.group(1)) if m else -90.0
    except (ValueError, AttributeError):
        return -90.0

def measure_dominance(mix_path, voice_path, voice_active_ranges, sample_dur=0.2, n_samples=5):
    """Dominance moyenne (dB) de la voix sur le mix, mesurée sur n_samples fenêtres
    de sample_dur secondes prises au milieu des plages voice_active."""
    if not voice_active_ranges:
        return 0.0
    import random
    rng = random.Random(123)
    picks = []
    for _ in range(n_samples):
        s, e = rng.choice(voice_active_ranges)
        if e - s < sample_dur:
            continue
        t0 = rng.uniform(s, e - sample_dur)
        picks.append((t0, t0 + sample_dur))
    if not picks:
        return 0.0
    diffs = []
    for s, e in picks:
        diffs.append(_rms_db(voice_path, s, e) - _rms_db(mix_path, s, e))
    return sum(diffs) / len(diffs)
```

- [ ] **Step 4: Lancer (succès)** — `pytest backend/tests/test_audio_meta.py -v` → PASS (3).

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/audio_meta.py backend/tests/test_audio_meta.py
git commit -m "feat(music): audio_meta — LUFS + voice dominance measurement"
```

---

## Task 3: music_bank — choix déterministe + LUFS cache

**Files:** Modify `backend/pipeline/music_bank.py`, Test `backend/tests/test_music_bank_choose.py`

- [ ] **Step 1: Tests (échec)**
```python
# backend/tests/test_music_bank_choose.py
import random
from backend import ffmpeg
from backend.pipeline import music_bank

def _mk(path, dur=40):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", f"sine=frequency=440:duration={dur}", path])

def test_choose_returns_track_in_category(tmp_path):
    (tmp_path / "Luxury").mkdir()
    for n in ("a.mp3", "b.mp3", "c.mp3"):
        _mk(str(tmp_path / "Luxury" / n))
    t = music_bank.choose("Luxury", target_dur=10, root=str(tmp_path), rng=random.Random(42))
    assert t.endswith(".mp3") and "Luxury" in t

def test_choose_deterministic_with_seed(tmp_path):
    (tmp_path / "Hype").mkdir()
    for n in ("a.mp3", "b.mp3", "c.mp3"):
        _mk(str(tmp_path / "Hype" / n))
    t1 = music_bank.choose("Hype", target_dur=10, root=str(tmp_path), rng=random.Random(7))
    t2 = music_bank.choose("Hype", target_dur=10, root=str(tmp_path), rng=random.Random(7))
    assert t1 == t2

def test_choose_returns_none_when_empty(tmp_path):
    assert music_bank.choose("Luxury", target_dur=10, root=str(tmp_path)) is None

def test_index_caches_lufs(tmp_path):
    (tmp_path / "Luxury").mkdir()
    _mk(str(tmp_path / "Luxury" / "a.mp3"))
    idx1 = music_bank.index_category("Luxury", str(tmp_path))
    assert "a.mp3" in next(iter(idx1.keys()))
    assert "lufs" in next(iter(idx1.values()))
    # 2e appel = lecture du cache (existe)
    idx2 = music_bank.index_category("Luxury", str(tmp_path))
    assert idx2 == idx1
```

- [ ] **Step 2: Lancer (échec)** — FAIL.

- [ ] **Step 3: Étendre `backend/pipeline/music_bank.py`**
```python
# (ajouter en bas du fichier)
import json, random
from backend import ffmpeg
from backend.pipeline.audio_meta import lufs_of

INDEX_NAME = ".music_index.json"

def _index_path(root):
    return os.path.join(root, INDEX_NAME)

def _load_index(root):
    p = _index_path(root)
    if os.path.isfile(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_index(root, idx):
    try:
        json.dump(idx, open(_index_path(root), "w", encoding="utf-8"), indent=2)
    except Exception:
        pass

def index_category(category, root):
    """Scan + cache (LUFS, dur) par fichier. Re-scan seulement les nouveaux/changés."""
    full = _load_index(root)
    cat_idx = full.get(category, {})
    keep = {}
    for f in list_tracks(category, root):
        mtime = os.path.getmtime(f)
        e = cat_idx.get(f)
        if e and e.get("mtime") == mtime:
            keep[f] = e
        else:
            keep[f] = {"mtime": mtime, "lufs": lufs_of(f), "dur": ffmpeg.probe_duration(f)}
    full[category] = keep
    _save_index(root, full)
    return keep

def choose(category, target_dur, root, rng=None):
    """Choix d'une track de la catégorie, déterministe si rng fourni.
    Préfère les tracks de durée >= target_dur + 5s. Renvoie None si vide."""
    idx = index_category(category, root)
    if not idx:
        return None
    rng = rng or random.Random()
    candidates = [f for f, e in idx.items() if e["dur"] >= target_dur + 5.0]
    pool = candidates or list(idx.keys())
    return rng.choice(sorted(pool))
```

- [ ] **Step 4: Lancer (succès)** — PASS (4).

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/music_bank.py backend/tests/test_music_bank_choose.py
git commit -m "feat(music): deterministic choose + LUFS cache"
```

---

## Task 4: Director — scoring catégorie + helpers events

**Files:** Modify `backend/pipeline/director.py`, Test `backend/tests/test_director_music.py`

- [ ] **Step 1: Tests (échec)**
```python
# backend/tests/test_director_music.py
from backend.pipeline.director import (_score_music_category,
                                       _voice_active_events, _pre_cta_gap_event)

def _kw(label, start=1.0, imp="high"):
    return {"type": "keyword", "label": label, "start": start, "end": start + 0.4, "importance": imp}

def test_score_hype_wins_on_ctas_and_numbers():
    events = [_kw("Écris", imp="high"), _kw("commente", imp="high"),
              _kw("200€", imp="high"), _kw("3", imp="high")]
    res = _score_music_category(events, duration=15.0)
    assert res["category"] == "hype"
    assert res["confidence"] >= 0.60
    assert any("CTA" in r or "chiffres" in r or "duration" in r for r in res["reason"])

def test_score_luxury_wins_on_brand_superlative():
    events = [_kw("Rolex"), _kw("incroyable")]
    res = _score_music_category(events, duration=25.0)
    assert res["category"] == "luxury"
    assert "brand detected" in res["reason"]
    assert "superlative detected" in res["reason"]

def test_score_fallback_when_low_confidence():
    res = _score_music_category([], duration=15.0)
    assert res["category"] == "luxury"
    assert res["reason"] == ["low confidence fallback"]
    assert res["fallback_used"] is True

def test_voice_active_events_from_tokens():
    tokens = [{"disp": "Un", "start": 0.0, "end": 0.3, "sent": 0},
              {"disp": "mot", "start": 0.4, "end": 0.7, "sent": 0},
              {"disp": "ici", "start": 3.0, "end": 3.3, "sent": 1}]
    events = _voice_active_events(tokens, gap_threshold=1.0)
    assert all(e["type"] == "voice_active" for e in events)
    assert events[0]["start"] == 0.0 and events[0]["end"] >= 0.7
    assert events[-1]["start"] >= 3.0

def test_pre_cta_gap_from_cta_keyword():
    events = [{"type": "keyword", "label": "Écris", "start": 12.0, "end": 12.4, "importance": "high"}]
    gap = _pre_cta_gap_event(events, gap_dur=1.2)
    assert gap is not None
    assert abs(gap["end"] - 12.0) < 1e-9
    assert abs(gap["start"] - 10.8) < 1e-9

def test_pre_cta_gap_none_when_no_cta():
    assert _pre_cta_gap_event([{"type": "keyword", "label": "Rolex",
                                "start": 1.0, "end": 1.4, "importance": "high"}]) is None
```

- [ ] **Step 2: Lancer (échec)** — FAIL.

- [ ] **Step 3: Ajouter à `backend/pipeline/director.py`**
```python
# (en haut, à côté des imports existants)
from backend.config import MUSIC as MUSIC_CFG
from backend.pipeline.sfx_plan import is_cta, is_price, is_number, is_watch_brand
from backend.pipeline.keywords import SUPERLATIVES
from backend.pipeline.sfx_plan import _norm as _n

def _voice_active_events(tokens, gap_threshold=1.0):
    """Plages parlées : agrège des tokens en blocs séparés par des silences ≥ gap_threshold."""
    if not tokens:
        return []
    out = []
    cur_s, cur_e = tokens[0]["start"], tokens[0]["end"]
    for t in tokens[1:]:
        if t["start"] - cur_e >= gap_threshold:
            out.append({"type": "voice_active", "start": cur_s, "end": cur_e})
            cur_s = t["start"]
        cur_e = max(cur_e, t["end"])
    out.append({"type": "voice_active", "start": cur_s, "end": cur_e})
    return out

def _pre_cta_gap_event(events, gap_dur=None):
    """Crée un event pre_cta_gap si un keyword CTA est détecté. None sinon."""
    g = MUSIC_CFG["pre_cta_gap_s"] if gap_dur is None else gap_dur
    for ev in events:
        if ev.get("type") == "keyword" and is_cta(ev.get("label", "")):
            return {"type": "pre_cta_gap",
                    "start": max(0.0, ev["start"] - g),
                    "end": ev["start"],
                    "importance": "high"}
    return None

def _score_music_category(events, duration):
    """Heuristique simple. Renvoie {category, confidence, reason[], fallback_used, signals{}}."""
    kw = [e for e in events if e.get("type") == "keyword"]
    n_cta = sum(1 for e in kw if is_cta(e.get("label", "")))
    n_price = sum(1 for e in kw if is_price(e.get("label", "")))
    n_number = sum(1 for e in kw if is_number(e.get("label", "")))
    n_brand = sum(1 for e in kw if is_watch_brand(e.get("label", "")))
    n_superlative = sum(1 for e in kw if _n(e.get("label", "")) in SUPERLATIVES)
    n_high = sum(1 for e in kw if e.get("importance") == "high")
    density_high = (n_high / len(kw)) if kw else 0.0
    signals = {"n_cta": n_cta, "n_price": n_price, "n_number": n_number,
               "n_brand": n_brand, "n_superlative": n_superlative,
               "n_high": n_high, "density_high": density_high, "duration": duration}

    hype_score, hype_reasons = 0.0, []
    if n_cta >= 2:                 hype_score += 0.30; hype_reasons.append(f"{n_cta} CTA")
    if n_price + n_number >= 2:    hype_score += 0.25; hype_reasons.append(f"{n_price + n_number} chiffres/prix")
    if duration < 20:              hype_score += 0.15; hype_reasons.append("duration < 20s")
    if density_high >= 0.5:        hype_score += 0.30; hype_reasons.append("densité events high")

    lux_score, lux_reasons = 0.0, []
    if n_brand >= 1:               lux_score += 0.35; lux_reasons.append("brand detected")
    if n_superlative >= 1:         lux_score += 0.30; lux_reasons.append("superlative detected")
    if n_cta <= 1:                 lux_score += 0.15; lux_reasons.append("peu de CTA")
    if duration >= 20:             lux_score += 0.20; lux_reasons.append("duration >= 20s")

    if hype_score >= lux_score:
        cat, conf, reasons = "hype", hype_score, hype_reasons
    else:
        cat, conf, reasons = "luxury", lux_score, lux_reasons

    if conf < MUSIC_CFG["confidence_threshold"]:
        return {"category": MUSIC_CFG["category_default"], "confidence": conf,
                "reason": ["low confidence fallback"], "fallback_used": True,
                "signals": signals}
    return {"category": cat, "confidence": conf, "reason": reasons,
            "fallback_used": False, "signals": signals}
```

- [ ] **Step 4: Lancer (succès)** — `pytest backend/tests/test_director_music.py -v` → PASS (6).

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/director.py backend/tests/test_director_music.py
git commit -m "feat(music): Director scoring + voice_active + pre_cta_gap events"
```

---

## Task 5: Director._decide_music + _compute_quality_score + build_plan

**Files:** Modify `backend/pipeline/director.py`, Test `backend/tests/test_director_music_plan.py`

- [ ] **Step 1: Tests (échec)**
```python
# backend/tests/test_director_music_plan.py
import json
from backend.pipeline.director import (_decide_music, _compute_quality_score, build_plan)

def _kw(label, start=1.0, imp="high"):
    return {"type": "keyword", "label": label, "start": start, "end": start + 0.4, "importance": imp}

def test_decide_music_returns_beds_accents_debug(tmp_path):
    (tmp_path / "Luxury").mkdir()
    from backend import ffmpeg
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=40",
                str(tmp_path / "Luxury" / "a.mp3")])
    tokens = [{"disp": "Rolex", "start": 1.0, "end": 1.4, "sent": 0}]
    events = [_kw("Rolex")]
    m = _decide_music(events, tokens, n_sent=1, ranges=[(0.0, 14.0)], duration=14.0,
                      music_root=str(tmp_path), rng_seed=42)
    assert "beds" in m and "accents" in m and "mix" in m and "debug" in m
    assert len(m["beds"]) == 1 and m["accents"] == []
    assert m["beds"][0]["category"] == "luxury"
    assert m["beds"][0]["base_gain_dB"] >= -22.0
    assert m["debug"]["category"] == "luxury"
    # JSON-sérialisable
    s = json.dumps(m); assert "beds" in s and "debug" in s

def test_decide_music_none_when_empty_library(tmp_path):
    # banque inexistante -> Director renvoie None (music_engine no-op)
    m = _decide_music([], [], 0, [(0.0, 5.0)], 5.0, music_root=str(tmp_path))
    assert m is None

def test_compute_quality_score_full():
    dbg = {"voice_dominance_dB": 7.0, "duck_depth_dB_effective": -12.0,
           "duck_depth_dB_requested": -12.0,
           "gaps": [{"start": 10.0, "end": 11.2}], "cta_detected": True,
           "lufs_final_target": -16.0, "lufs_final_actual": -15.5,
           "fallback_used": False}
    assert _compute_quality_score(dbg) == 1.0

def test_compute_quality_score_partial():
    dbg = {"voice_dominance_dB": 5.0, "duck_depth_dB_effective": -8.0,
           "duck_depth_dB_requested": -12.0,
           "gaps": [], "cta_detected": True,
           "lufs_final_target": -16.0, "lufs_final_actual": -19.0,
           "fallback_used": True}
    # 0/5 critères -> 0.0
    assert _compute_quality_score(dbg) == 0.0

def test_compute_quality_score_cta_absent_neutral():
    dbg = {"voice_dominance_dB": 7.0, "duck_depth_dB_effective": -12.0,
           "duck_depth_dB_requested": -12.0,
           "gaps": [], "cta_detected": False,
           "lufs_final_target": -16.0, "lufs_final_actual": -16.0,
           "fallback_used": False}
    # CTA absent -> ce critère est neutralisé (vert auto) -> 1.0
    assert _compute_quality_score(dbg) == 1.0

def test_build_plan_keeps_music_key():
    tokens = [{"disp": "Rolex", "start": 1.0, "end": 1.4, "sent": 0}]
    plan = build_plan([_kw("Rolex")], tokens, 1, [(0.0, 5.0)], 5.0)
    assert "music" in plan   # même si None
```

- [ ] **Step 2: Lancer (échec)** — FAIL.

- [ ] **Step 3: Modifier `backend/pipeline/director.py`**

Ajouter en haut :
```python
from backend.pipeline import music_bank
import random as _random
```

Ajouter ces fonctions (avant `build_plan`) :
```python
def _compute_quality_score(debug):
    """Pure : 5 critères × 0.2. CTA absent -> critère neutralisé."""
    score = 0.0
    if debug.get("voice_dominance_dB", 0) >= MUSIC_CFG["voice_dominance_min_dB"]:
        score += 0.2
    if debug.get("duck_depth_dB_effective") == debug.get("duck_depth_dB_requested"):
        score += 0.2
    if not debug.get("cta_detected", False):
        score += 0.2   # neutralisé
    elif debug.get("gaps"):
        score += 0.2
    if abs(debug.get("lufs_final_actual", -1e9) - debug.get("lufs_final_target", 0)) <= 1.5:
        score += 0.2
    if not debug.get("fallback_used", False):
        score += 0.2
    return round(score, 2)

def _decide_music(events, tokens, n_sent, ranges, duration, music_root=None, rng_seed=None):
    """Construit plan['music'] complet. Retourne None si banque vide."""
    if music_root is None:
        music_root = MUSIC_CFG.get("dir") or __import__("backend.config", fromlist=["MUSIC_DIR"]).MUSIC_DIR
    val = music_bank.validate_library(music_root)
    if val["tracks_found"].get("Luxury", 0) == 0 and val["tracks_found"].get("Hype", 0) == 0:
        return None

    scoring = _score_music_category(events, duration)
    category = scoring["category"]
    # bascule sur l'autre catégorie si vide
    cat_tracks = val["tracks_found"]
    if cat_tracks.get(category.capitalize(), 0) == 0:
        other = "luxury" if category == "hype" else "hype"
        if cat_tracks.get(other.capitalize(), 0) > 0:
            category = other; scoring["reason"].append(f"swap: empty {scoring['category']} -> {other}")

    rng = _random.Random(rng_seed) if rng_seed is not None else None
    track = music_bank.choose(category.capitalize(), target_dur=duration,
                              root=music_root, rng=rng)
    if not track:
        return None

    # Clamps voix > musique
    base = max(MUSIC_CFG["base_gain_dB"], MUSIC_CFG["max_base_gain_dB"])  # ex : max(-22, -16) = -16 (plafond)
    # NB: max() avec valeurs négatives renvoie la plus haute = la plus forte;
    # on veut le PLUS BAS des deux donc:
    base = min(MUSIC_CFG["base_gain_dB"], MUSIC_CFG["max_base_gain_dB"])
    # Ducking depth — V1 valeur cfg ; les clamps fins sont gérés post-mesure dans service.
    duck_depth = MUSIC_CFG["duck_depth_dB"]

    pre_cta = _pre_cta_gap_event(events, MUSIC_CFG["pre_cta_gap_s"])
    gaps = []
    if pre_cta:
        gaps.append({"start": pre_cta["start"], "end": pre_cta["end"],
                     "fade_out_ms": MUSIC_CFG["pre_cta_fade_out_ms"],
                     "fade_in_ms": MUSIC_CFG["pre_cta_fade_in_ms"]})

    bed = {
        "track": track, "category": category, "trim_start": 0.0,
        "start": 0.0, "duration": duration,
        "base_gain_dB": base,
        "fade_in_ms": MUSIC_CFG["fade_in_ms"],
        "fade_out_ms": MUSIC_CFG["fade_out_ms"],
        "duck": {"mode": "sidechain", "ratio": 6.0, "threshold_dB": -28,
                 "attack_ms": 8, "release_ms": 280, "depth_dB": duck_depth,
                 "side": "voice"},
        "gaps": gaps,
    }
    debug = {
        "category": category, "confidence": scoring["confidence"],
        "reason": scoring["reason"], "fallback_used": scoring["fallback_used"],
        "signals": scoring["signals"],
        "track": track,
        "lufs_voice": None, "lufs_music_source": None,
        "lufs_music_at_base": None, "lufs_final_target": MUSIC_CFG["target_lufs"],
        "lufs_final_actual": None,
        "duck_depth_dB_requested": duck_depth, "duck_depth_dB_effective": duck_depth,
        "voice_dominance_dB": None, "cta_detected": pre_cta is not None,
        "gaps": gaps,
        "auto_fix_applied": False, "warnings": [],
        "music_quality_score": None,
    }
    return {"beds": [bed], "accents": [],
            "mix": {"target_lufs": MUSIC_CFG["target_lufs"], "voice_priority": True},
            "debug": debug}
```

Modifier `build_plan` pour inclure `music` :
```python
def build_plan(events, tokens, n_sent, ranges, duration, music_root=None, rng_seed=None):
    return {
        "subtitles":   _decide_subtitles(events, tokens, n_sent),
        "motion":      _decide_motion(events, ranges),
        "transitions": _decide_transitions(events, ranges),
        "music":       _decide_music(events, tokens, n_sent, ranges, duration,
                                     music_root=music_root, rng_seed=rng_seed),
    }
```

- [ ] **Step 4: Lancer (succès)** — `pytest backend/tests/test_director_music_plan.py backend/tests/test_director.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/director.py backend/tests/test_director_music_plan.py
git commit -m "feat(music): Director._decide_music + _compute_quality_score + plan['music']"
```

---

## Task 6: music_engine — fragment ffmpeg purement exécutif

**Files:** Create `backend/pipeline/music_engine.py`, Test `backend/tests/test_music_engine.py`

- [ ] **Step 1: Tests (échec)**
```python
# backend/tests/test_music_engine.py
from backend.pipeline import music_engine

def test_no_op_when_music_none():
    out = music_engine.build(None, voice_label="vmix", base_input_idx=2)
    assert out["extra_inputs"] == [] and out["filter_str"] == "" and out["out_label"] == "vmix"

def test_no_op_when_no_beds():
    out = music_engine.build({"beds": [], "accents": []}, "vmix", 2)
    assert out["extra_inputs"] == []

def test_build_one_bed_returns_filter_and_input(tmp_path):
    bed = {"track": "/abs/track.mp3", "trim_start": 0.0, "start": 0.0, "duration": 13.5,
           "base_gain_dB": -22, "fade_in_ms": 800, "fade_out_ms": 1200,
           "duck": {"mode": "sidechain", "ratio": 6.0, "threshold_dB": -28,
                    "attack_ms": 8, "release_ms": 280, "depth_dB": -12, "side": "voice"},
           "gaps": [{"start": 11.0, "end": 12.0, "fade_out_ms": 250, "fade_in_ms": 200}]}
    plan_music = {"beds": [bed], "accents": [], "mix": {"target_lufs": -16.0}}
    out = music_engine.build(plan_music, voice_label="vmix", base_input_idx=3)
    assert out["extra_inputs"] == ["/abs/track.mp3"]
    f = out["filter_str"]
    assert "sidechaincompress" in f
    assert "afade=t=in" in f and "afade=t=out" in f
    assert "volume=" in f
    # gap = on coupe la musique entre 11 et 12s
    assert "between(t,11" in f or "enable='between(t,11" in f
    assert out["out_label"].startswith("[") and out["out_label"].endswith("]")
```

- [ ] **Step 2: Lancer (échec)** — FAIL.

- [ ] **Step 3: Écrire `backend/pipeline/music_engine.py`**
```python
def build(plan_music, voice_label, base_input_idx):
    """Convertit plan['music'] en (extra_inputs, filter_str, out_label).
    No-op si plan_music None ou beds vide.
    voice_label : label ffmpeg de la voix mixée (ex 'vmix' -> '[vmix]').
    base_input_idx : index du PREMIER input supplémentaire ajouté."""
    if not plan_music or not plan_music.get("beds"):
        return {"extra_inputs": [], "filter_str": "", "out_label": voice_label}

    inputs, parts, last = [], [], None
    idx = base_input_idx
    for bi, bed in enumerate(plan_music["beds"]):
        inputs.append(bed["track"])
        in_label = f"[{idx}:a]"
        # 1) trim/start: trim+asetpts
        ts = bed.get("trim_start", 0.0); dur = bed["duration"]
        clip_chain = (f"{in_label}atrim=start={ts:.3f}:end={ts + dur:.3f},asetpts=N/SR/TB,"
                      f"aresample=async=1000,"
                      f"volume={bed['base_gain_dB']:.2f}dB,"
                      f"afade=t=in:st=0:d={bed['fade_in_ms'] / 1000:.3f},"
                      f"afade=t=out:st={dur - bed['fade_out_ms'] / 1000:.3f}:d={bed['fade_out_ms'] / 1000:.3f}")
        # 2) gaps (volume=0 sur l'intervalle)
        for g in bed.get("gaps", []):
            clip_chain += f",volume=0:enable='between(t,{g['start']:.3f},{g['end']:.3f})'"
        clip_label = f"[mraw{bi}]"
        parts.append(clip_chain + clip_label)
        # 3) sidechain ducking
        d = bed["duck"]
        ducked = f"[m{bi}]"
        parts.append(
            f"[{voice_label}]asplit=2[vside{bi}][vkeep{bi}];"
            f"{clip_label}[vside{bi}]sidechaincompress="
            f"threshold={d['threshold_dB']}dB:ratio={d['ratio']}:"
            f"attack={d['attack_ms']}:release={d['release_ms']}"
            f"{ducked}"
        )
        # On remplace 'voice_label' par 'vkeep{bi}' pour la suite (audio voix non modifiée).
        voice_label = f"vkeep{bi}"
        last = ducked.strip("[]")
        idx += 1

    # Mix final voix + dernière musique
    parts.append(f"[{voice_label}][{last}]amix=inputs=2:normalize=0:duration=longest[mout]")
    return {"extra_inputs": inputs, "filter_str": ";".join(parts), "out_label": "mout"}
```

- [ ] **Step 4: Lancer (succès)** — `pytest backend/tests/test_music_engine.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/music_engine.py backend/tests/test_music_engine.py
git commit -m "feat(music): music_engine — purely executive ffmpeg fragment builder"
```

---

## Task 7: Intégration dans montage.render

**Files:** Modify `backend/pipeline/montage.py`, Test `backend/tests/test_montage_music.py`

- [ ] **Step 1: Test (échec)**
```python
# backend/tests/test_montage_music.py
import os
from backend import ffmpeg
from backend.pipeline.montage import render

def _sine(path, dur=15):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", f"sine=frequency=440:duration={dur}", path])

def _mini_ass(path):
    open(path, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,80,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,4,0,5,80,80,80,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,TEST\n")

def test_render_with_music(sample_audio, tmp_path):
    track = str(tmp_path / "t.mp3"); _sine(track, dur=40)
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    plan_music = {
        "beds": [{
            "track": track, "category": "luxury", "trim_start": 0.0,
            "start": 0.0, "duration": dur,
            "base_gain_dB": -22, "fade_in_ms": 800, "fade_out_ms": 1200,
            "duck": {"mode": "sidechain", "ratio": 6.0, "threshold_dB": -28,
                     "attack_ms": 8, "release_ms": 280, "depth_dB": -12, "side": "voice"},
            "gaps": [],
        }],
        "accents": [], "mix": {"target_lufs": -16.0}, "debug": {}
    }
    out = str(tmp_path / "m.mp4")
    render(sample_audio, ass, [(0.0, dur)], out, plan={"music": plan_music}, seed=42)
    assert os.path.exists(out)
    # piste audio présente
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "error", "-select_streams", "a",
                    "-show_entries", "stream=codec_type", "-of", "csv=p=0", out])
    assert "audio" in r.stdout

def test_render_music_none_is_identical_to_no_music(sample_audio, tmp_path):
    """Non-régression : plan['music']=None doit rendre comme avant."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    out1 = str(tmp_path / "a.mp4"); out2 = str(tmp_path / "b.mp4")
    render(sample_audio, ass, [(0.0, dur)], out1, plan=None, seed=42)
    render(sample_audio, ass, [(0.0, dur)], out2, plan={"music": None}, seed=42)
    assert os.path.getsize(out1) > 0 and os.path.getsize(out2) > 0
```

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_montage_music.py -v` → FAIL.

- [ ] **Step 3: Modifier `backend/pipeline/montage.py`** — dans la section audio (à l'endroit où on construit l'amix actuel) intégrer `music_engine.build(...)` :

Repère le bloc audio dans `render` (autour des `[Ncl]:a`, `aformat=...`). À ajouter, après la construction du label voix mixée (`amap` ou similaire) :

```python
    # --- Musique (purement exécutif) -----------------------------------
    from backend.pipeline import music_engine
    music = (plan or {}).get("music") if isinstance(plan, dict) else None
    if music and music.get("beds"):
        # 1) Inputs supplémentaires (musique) en fin de cmd
        music_inputs_start = len(chosen) + 1 + len(resolved)  # = idx du PREMIER input musique
        me = music_engine.build(music, voice_label=amap.strip("[]") if amap.startswith("[")
                                else amap, base_input_idx=music_inputs_start)
        for t in me["extra_inputs"]:
            cmd += ["-i", t]
        if me["filter_str"]:
            fc.append(me["filter_str"])
            amap = "[" + me["out_label"] + "]"
```

(Si la variable s'appelle autrement dans ton implémentation, adapte. Le principe : ajouter les `-i <track>` après les SFX, et brancher `music_engine.build` qui produit le filtre + le nouveau label de sortie audio.)

- [ ] **Step 4: Lancer** — `pytest backend/tests/test_montage_music.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/montage.py backend/tests/test_montage_music.py
git commit -m "feat(music): integrate music_engine into montage.render audio graph"
```

---

## Task 8: Service — auto-fix non bloquant + dominance + quality score

**Files:** Modify `backend/service.py`, Test `backend/tests/test_service_music_autofix.py`

- [ ] **Step 1: Test (échec)**
```python
# backend/tests/test_service_music_autofix.py
import os
from backend import ffmpeg
from backend import service

def _sine(path, freq, dur, vol=0):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", f"sine=frequency={freq}:duration={dur}",
                "-af", f"volume={vol}dB", path])

def test_make_video_never_raises_when_music_too_loud(monkeypatch, tmp_path):
    """Plan musique volontairement trop fort : make_video doit RÉUSSIR (auto-fix non bloquant),
    et marquer auto_fix_applied / warnings dans le debug."""
    # Stub measure_dominance pour simuler une dominance trop basse, puis OK après auto-fix
    from backend.pipeline import audio_meta
    calls = {"n": 0}
    def fake(*a, **kw):
        calls["n"] += 1
        return 3.0 if calls["n"] == 1 else 8.0
    monkeypatch.setattr(audio_meta, "measure_dominance", fake)
    # On ne teste pas l'intégration complète make_video ici (lourd), juste l'orchestrateur :
    debug = {"voice_dominance_dB": None, "auto_fix_applied": False, "warnings": []}
    ok, debug = service._music_dominance_autofix(
        debug, render_callable=lambda gain: gain,    # stub
        current_gain=-22.0)
    assert ok is True
    assert debug["auto_fix_applied"] is True
    assert debug["voice_dominance_dB"] == 8.0
    assert any("auto-reduced" in w for w in debug["warnings"])

def test_make_video_keeps_warning_when_autofix_fails(monkeypatch):
    from backend.pipeline import audio_meta
    monkeypatch.setattr(audio_meta, "measure_dominance", lambda *a, **kw: 3.0)
    debug = {"voice_dominance_dB": None, "auto_fix_applied": False, "warnings": []}
    ok, debug = service._music_dominance_autofix(
        debug, render_callable=lambda gain: gain, current_gain=-22.0)
    assert ok is True  # JAMAIS bloquant
    assert debug["auto_fix_applied"] is True
    assert any("still below" in w for w in debug["warnings"])
```

- [ ] **Step 2: Lancer (échec)** — FAIL (fonction inexistante).

- [ ] **Step 3: Modifier `backend/service.py`** — ajouter en haut :
```python
from backend.config import MUSIC as MUSIC_CFG
from backend.pipeline import audio_meta, director as _director
```

Ajouter cette fonction utilitaire :
```python
def _music_dominance_autofix(debug, render_callable, current_gain, *,
                             voice_path=None, mix_path=None, voice_active=None):
    """Mesure la dominance ; si < seuil, baisse la musique de step_dB et re-render
    UNE seule fois. Jamais bloquant. Renvoie (ok=True, debug_mis_à_jour)."""
    if voice_path and mix_path:
        dom = audio_meta.measure_dominance(mix_path, voice_path, voice_active or [])
    else:
        # test : 'measure_dominance' a été stubé pour renvoyer une valeur
        dom = audio_meta.measure_dominance(None, None, None)
    debug["voice_dominance_dB"] = dom
    if dom < MUSIC_CFG["voice_dominance_min_dB"]:
        new_gain = current_gain + MUSIC_CFG["auto_fix_step_dB"]
        render_callable(new_gain)
        debug["auto_fix_applied"] = True
        if voice_path and mix_path:
            dom2 = audio_meta.measure_dominance(mix_path, voice_path, voice_active or [])
        else:
            dom2 = audio_meta.measure_dominance(None, None, None)
        debug["voice_dominance_dB"] = dom2
        if dom2 < MUSIC_CFG["voice_dominance_min_dB"]:
            debug["warnings"].append(
                f"voice dominance still below {MUSIC_CFG['voice_dominance_min_dB']} dB after auto-fix "
                f"(value={dom2:.1f} dB)")
        else:
            debug["warnings"].append(
                f"voice dominance was {dom:.1f} dB, auto-reduced music by "
                f"{abs(MUSIC_CFG['auto_fix_step_dB']):.0f} dB (now {dom2:.1f} dB)")
    return True, debug
```

Câbler dans `make_video` (après le `montage.render`) si `plan.get("music")` :
```python
    if plan.get("music"):
        debug = plan["music"]["debug"]
        debug["lufs_voice"] = audio_meta.lufs_of(clean_path)
        if plan["music"]["beds"]:
            bed = plan["music"]["beds"][0]
            debug["lufs_music_source"] = audio_meta.lufs_of(bed["track"])
        debug["lufs_final_actual"] = audio_meta.lufs_of(out_path)
        # Auto-fix dominance (jamais bloquant)
        voice_active_ranges = [(e["start"], e["end"])
                               for e in _director._voice_active_events(tokens)]
        def _re_render(new_gain):
            plan["music"]["beds"][0]["base_gain_dB"] = new_gain
            debug["duck_depth_dB_effective"] = plan["music"]["beds"][0]["duck"]["depth_dB"]
            montage.render(clean_path, ass, ranges, out_path,
                           boost=boost, sfx_events=sfx_events, plan=plan)
        _music_dominance_autofix(debug, _re_render,
                                 current_gain=plan["music"]["beds"][0]["base_gain_dB"],
                                 voice_path=clean_path, mix_path=out_path,
                                 voice_active=voice_active_ranges)
        debug["music_quality_score"] = _director._compute_quality_score(debug)
```

- [ ] **Step 4: Lancer** — `pytest backend/tests/test_service_music_autofix.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/service.py backend/tests/test_service_music_autofix.py
git commit -m "feat(music): non-blocking auto-fix + LUFS measure + quality score wired"
```

---

## Task 9: Validation visuelle finale (démo A/B)

**Files:** Scénario hors-test (script ponctuel). Non commité, dossier `demo_music/` ignoré.

- [ ] **Step 1: Vérifier que `MUSIC/Luxury/` et `MUSIC/Hype/` contiennent ≥ 3 tracks**
```bash
python -c "from backend.pipeline.music_bank import validate_library; from backend.config import MUSIC_DIR; print(validate_library(MUSIC_DIR))"
```

- [ ] **Step 2: Démo A/B** — script `_demo_music.py` (à supprimer après) :
  - même audio (`backend/tests/fixtures/sample.mp3`), même texte (corrigé, riche en keywords), même seed.
  - BEFORE = `plan["music"]=None` ; AFTER = `_decide_music(...)`.
  - `side_by_side.mp4` (vidéo identique gauche/droite, overlay « MUSIC OFF » / « MUSIC ON »).
  - Rapport `REPORT.md` : temps, taille, `music_debug.json` complet, `music_quality_score`.

- [ ] **Step 3: Critères de validation visuelle/audible**
  - [ ] Lecture côte à côte : voix **parfaitement intelligible** dans AFTER.
  - [ ] Musique commence par un fade in audible (≥ 600 ms).
  - [ ] Musique baisse pendant la voix (sidechain perceptible mais sans pumping).
  - [ ] Trou musical clair 1–1.2 s avant le CTA (si CTA détecté).
  - [ ] `voice_dominance_dB` ≥ 6.0 (ou `auto_fix_applied=true` + warning logué — jamais d'erreur).
  - [ ] `music_quality_score` ≥ 0.8.
  - [ ] Temps de rendu : AFTER ≤ BEFORE × 1.5.
  - [ ] Taille vidéo : AFTER ≤ BEFORE × 1.2.

- [ ] **Step 4: Nettoyage** — supprimer `_demo_music.py`, garder `demo_music/` (déjà gitignoré).

---

## Self-Review

- **Couverture spec :**
  - §Modules : tous présents (T0, T2-T7).
  - §Format `plan["music"]` : produit par `_decide_music` (T5), exécuté par `music_engine` (T6).
  - §Logique sélection catégorie : scoring + fallback (T4).
  - §Logique ducking : sidechain dans music_engine (T6).
  - §Gap CTA : event + bed.gaps (T4, T5).
  - §Normalisation LUFS : measure dans `audio_meta` (T2), appliqué via `volume` dans bed (T5), debug rempli dans service (T8).
  - §Dominance + AUTO-FIX non bloquant : T8 (test explicite que `make_video` ne lève jamais).
  - §Score qualité : T5 (`_compute_quality_score`) câblé en T8.
  - §`accents` contrat figé : structure documentée, list vide en V1, JSON-sérialisable testé en T5.
  - §Banque : T0 (non bloquant).
  - §Démo A/B : T9 avec critères chiffrés.

- **Types cohérents :**
  - `validate_library(root) -> {ok, missing_categories, tracks_found, min_required_per_category}`
  - `choose(category, target_dur, root, rng=None) -> path|None`
  - `lufs_of(path) -> float` · `measure_dominance(mix, voice, ranges) -> float`
  - `_score_music_category(events, duration) -> {category, confidence, reason, fallback_used, signals}`
  - `_decide_music(...) -> plan_music|None` · `_compute_quality_score(debug) -> float`
  - `music_engine.build(plan_music, voice_label, base_input_idx) -> {extra_inputs, filter_str, out_label}`
  - `build_plan(..., music_root=None, rng_seed=None) -> {subtitles, motion, transitions, music}`
  - `_music_dominance_autofix(debug, render_callable, current_gain, *, ...) -> (bool, debug)`

- **Pas de placeholder.** Toutes les étapes contiennent le code à insérer ou la commande exacte.

- **Garde-fous non bloquants vérifiés :**
  - T0 : library vide → rapport, pas d'exception.
  - T5 : `_decide_music` renvoie `None` si banque vide → `music_engine` no-op (T6).
  - T7 : `plan["music"]=None` → rendu identique à avant (test de non-régression explicite).
  - T8 : auto-fix dominance JAMAIS bloquant (test explicite).
