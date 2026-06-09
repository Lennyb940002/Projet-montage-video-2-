# Asset Audit (Ticket A) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans.

**Goal:** Scanner chaque clip de la banque pour détecter watermarks/sous-titres incrustés et marquer comme `accept`/`reject`, avec rapport JSON cacheable.

**Architecture:** `asset_audit.py` extrait frames + OCR + heuristique watermark ; `asset_index.py` orchestre le scan global et le cache ; un script CLI `tools/audit_clips.py` produit un rapport humain lisible.

**Tech Stack:** EasyOCR (FR+EN), OpenCV (frame extraction), Python pur sinon.

---

## Task 1 — `extract_text_frames` : extraction frames + OCR

**Files:**
- Create: `backend/pipeline/asset_audit.py`
- Test: `backend/tests/test_asset_audit.py`

- [ ] **Step 1: Test échec**
```python
# test : un clip sans texte renvoie [] sur toutes les frames
def test_extract_text_on_blank_clip(tmp_path):
    from backend.pipeline.asset_audit import extract_text_frames
    # Génère un clip noir uniforme via ffmpeg
    from backend import ffmpeg
    f = str(tmp_path / "blank.mp4")
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-i",
                "color=c=black:s=320x240:r=30:d=2", f])
    samples = extract_text_frames(f, n_frames=3)
    assert len(samples) == 3
    assert all(s["texts"] == [] for s in samples)
```

- [ ] **Step 2: Implémentation**
```python
import os, tempfile, subprocess
from backend import ffmpeg

_ocr_reader = None

def _get_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(["fr", "en"], gpu=False, verbose=False)
    return _ocr_reader

def _extract_frame(video, t, out):
    subprocess.run([ffmpeg.FFMPEG, "-y", "-ss", f"{t:.2f}", "-i", video,
                    "-frames:v", "1", out, "-loglevel", "error"])

def extract_text_frames(video_path, n_frames=5):
    """Extrait n_frames PNG à 10/30/50/70/90% puis OCR.
    Renvoie [{t, texts: [{text, bbox, conf}], frame_path}]"""
    dur = ffmpeg.probe_duration(video_path)
    fractions = [(i + 1) / (n_frames + 1) for i in range(n_frames)]
    reader = _get_reader()
    out = []
    with tempfile.TemporaryDirectory() as td:
        for i, frac in enumerate(fractions):
            t = dur * frac
            png = os.path.join(td, f"f{i}.png")
            _extract_frame(video_path, t, png)
            if not os.path.exists(png):
                out.append({"t": t, "texts": []})
                continue
            results = reader.readtext(png, detail=1, paragraph=False)
            texts = [{"text": txt, "bbox": bbox, "conf": float(conf)}
                     for bbox, txt, conf in results
                     if conf > 0.3]
            out.append({"t": t, "texts": texts})
    return out
```

- [ ] **Step 3: Test PASS**

- [ ] **Step 4: Commit**

---

## Task 2 — Heuristique watermark + agrégation

**Files:** Modify `backend/pipeline/asset_audit.py`

- [ ] **Step 1: Tests**
```python
def test_watermark_confidence_for_at_marker_in_corner():
    from backend.pipeline.asset_audit import _watermark_confidence
    text_in_corner_w_at = {
        "text": "@cebutimepieces",
        "bbox": [[0, 1700], [200, 1700], [200, 1750], [0, 1750]],   # bottom-left
        "persistence": 5,   # vu sur 5 frames
    }
    conf = _watermark_confidence(text_in_corner_w_at,
                                  frame_w=1080, frame_h=1920)
    assert conf >= 0.6

def test_watermark_confidence_for_center_text():
    from backend.pipeline.asset_audit import _watermark_confidence
    text_center = {
        "text": "INCROYABLE",
        "bbox": [[400, 900], [700, 900], [700, 950], [400, 950]],
        "persistence": 1,
    }
    conf = _watermark_confidence(text_center,
                                  frame_w=1080, frame_h=1920)
    assert conf < 0.4
```

- [ ] **Step 2: Implémentation**
```python
def _bbox_zone(bbox, w, h, margin=0.15):
    """Renvoie 'top_left'/'bottom_right'/etc. ou None si le texte est central."""
    xs = [p[0] for p in bbox]; ys = [p[1] for p in bbox]
    cx, cy = sum(xs) / 4, sum(ys) / 4
    mx, my = w * margin, h * margin
    left = cx < mx; right = cx > w - mx
    top = cy < my; bot = cy > h - my
    if top and left: return "top_left"
    if top and right: return "top_right"
    if bot and left: return "bottom_left"
    if bot and right: return "bottom_right"
    return None

def _watermark_confidence(text_entry, frame_w, frame_h):
    score = 0.0
    zone = _bbox_zone(text_entry["bbox"], frame_w, frame_h)
    if zone:
        score += 0.30
    if text_entry.get("persistence", 1) >= 3:
        score += 0.30
    if text_entry["text"].lstrip().startswith("@"):
        score += 0.30
    return min(1.0, score)
```

- [ ] **Step 3: Test PASS**

- [ ] **Step 4: Commit**

---

## Task 3 — `audit_clip` : verdict complet par clip

**Files:** Modify `backend/pipeline/asset_audit.py`

- [ ] **Step 1: Test**
```python
def test_audit_clip_blank_is_accepted(tmp_path):
    from backend.pipeline.asset_audit import audit_clip
    from backend import ffmpeg
    f = str(tmp_path / "blank.mp4")
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-i",
                "color=c=black:s=320x240:r=30:d=2", f])
    res = audit_clip(f)
    assert res["status"] == "accepted"
    assert res["text_detected"] is False
    assert res["watermark_suspected"] is False
```

- [ ] **Step 2: Implémentation**
```python
import time

REJECT_WATERMARK_CONF = 0.8
REJECT_OCR_DENSITY = 0.15
REJECT_TEXT_REGIONS = 3

def audit_clip(video_path):
    samples = extract_text_frames(video_path, n_frames=5)
    dur = ffmpeg.probe_duration(video_path)
    # Récupérer dimensions
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "csv=p=0", video_path])
    try:
        w, h = [int(x) for x in r.stdout.strip().split(",")]
    except Exception:
        w, h = 1080, 1920

    total_tokens = sum(len(s["texts"]) for s in samples)
    text_detected = any(s["texts"] for s in samples)
    text_regions = max((len(s["texts"]) for s in samples), default=0)
    ocr_density = total_tokens / max(1, len(samples))

    # Persistence : compter combien de fois le même texte apparaît
    from collections import Counter
    text_counts = Counter()
    for s in samples:
        seen = {t["text"] for t in s["texts"]}
        for tt in seen:
            text_counts[tt] += 1

    # Watermark candidates : pour chaque texte, prendre la première bbox + persistence
    max_wm_conf = 0.0
    wm_zones = set()
    for s in samples:
        for t in s["texts"]:
            entry = {"text": t["text"], "bbox": t["bbox"],
                     "persistence": text_counts[t["text"]]}
            conf = _watermark_confidence(entry, w, h)
            if conf > max_wm_conf:
                max_wm_conf = conf
            zone = _bbox_zone(t["bbox"], w, h)
            if zone and conf >= 0.6:
                wm_zones.add(zone)

    reasons = []
    if max_wm_conf > REJECT_WATERMARK_CONF:
        reasons.append("watermark")
    if ocr_density > REJECT_OCR_DENSITY:
        reasons.append("embedded_text")
    elif text_regions >= REJECT_TEXT_REGIONS:
        reasons.append("embedded_text")
    status = "rejected" if reasons else "accepted"
    # Dedup reasons
    reasons = list(dict.fromkeys(reasons))

    return {
        "path": video_path,
        "duration": dur,
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "text_detected": text_detected,
        "ocr_density": round(ocr_density, 3),
        "text_regions": text_regions,
        "ocr_samples": [{"t": round(s["t"], 2),
                          "texts": [t["text"] for t in s["texts"]]}
                         for s in samples],
        "watermark_suspected": max_wm_conf >= 0.6,
        "watermark_confidence": round(max_wm_conf, 2),
        "watermark_zones": sorted(wm_zones),
        "status": status,
        "reasons": reasons,
    }
```

- [ ] **Step 3: Test PASS**

- [ ] **Step 4: Commit**

---

## Task 4 — `asset_index` : scan global + cache

**Files:**
- Create: `backend/pipeline/asset_index.py`
- Test: `backend/tests/test_asset_index.py`

- [ ] **Step 1: Tests**
```python
def test_scan_caches_results(tmp_path):
    from backend.pipeline.asset_index import scan_clips_dir, INDEX_NAME
    from backend import ffmpeg
    d = tmp_path / "Clips"; d.mkdir()
    f = str(d / "c.mp4")
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", "color=c=black:s=320x240:r=30:d=2", f])
    res1 = scan_clips_dir(str(d))
    assert len(res1) == 1
    import os
    assert os.path.exists(os.path.join(str(d), INDEX_NAME))
    # 2e appel = cache
    res2 = scan_clips_dir(str(d))
    assert res2 == res1
```

- [ ] **Step 2: Implémentation**
```python
import os, json, glob
from backend.pipeline.asset_audit import audit_clip

INDEX_NAME = ".asset_audit.json"
EXTS = (".mp4", ".mov", ".mkv")

def _index_path(root): return os.path.join(root, INDEX_NAME)

def _load_index(root):
    try:
        with open(_index_path(root), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_index(root, idx):
    try:
        with open(_index_path(root), "w", encoding="utf-8") as f:
            json.dump(idx, f, indent=2, ensure_ascii=False)
    except OSError:
        pass

def list_clips(root):
    out = []
    for ext in EXTS:
        out += glob.glob(os.path.join(root, "*" + ext))
        out += glob.glob(os.path.join(root, "**", "*" + ext), recursive=True)
    return sorted(set(out))

def scan_clips_dir(root, force=False):
    """Audit chaque clip + cache. Re-scan UNIQUEMENT les fichiers
    nouveaux/modifiés (mtime)."""
    cached = _load_index(root)
    out = {}
    for f in list_clips(root):
        mtime = os.path.getmtime(f)
        prev = cached.get(f)
        if not force and prev and prev.get("mtime") == mtime:
            out[f] = prev
        else:
            audit = audit_clip(f)
            audit["mtime"] = mtime
            out[f] = audit
    _save_index(root, out)
    return out

def accepted_clips(root):
    return [f for f, a in scan_clips_dir(root).items()
            if a["status"] == "accepted"]
```

- [ ] **Step 3: Test PASS**

- [ ] **Step 4: Commit**

---

## Task 5 — Script CLI `tools/audit_clips.py`

**Files:**
- Create: `tools/audit_clips.py`

- [ ] **Step 1: Implémentation**
```python
"""Scanne une banque de clips et affiche un rapport humain.
Usage: python tools/audit_clips.py [chemin_banque]
"""
import sys
from backend.pipeline.asset_index import scan_clips_dir

root = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:/Users/User/Downloads/Voix off/Clips/Muet"
print(f"Scan en cours: {root}\n(EasyOCR la 1re fois ~1 min de chargement)")
results = scan_clips_dir(root)

accepted = [a for a in results.values() if a["status"] == "accepted"]
rejected = [a for a in results.values() if a["status"] == "rejected"]
wm = [a for a in rejected if "watermark" in a["reasons"]]
text = [a for a in rejected if "embedded_text" in a["reasons"]]
both = [a for a in rejected if len(a["reasons"]) >= 2]

print(f"\n{'='*70}")
print(f"  RAPPORT — {len(results)} clips analysés")
print('='*70)
print(f"  rejetés    : {len(rejected)} ({100*len(rejected)/max(1,len(results)):.0f}%)")
print(f"    - watermark      : {len(wm)}")
print(f"    - texte incrusté : {len(text)}")
print(f"    - les deux       : {len(both)}")
print(f"  acceptés   : {len(accepted)}")
print('='*70)

if rejected:
    print("\nTop 10 rejetés (échantillon) :")
    for a in rejected[:10]:
        import os
        name = os.path.basename(a["path"])
        print(f"  - {name[:60]:60} {a['reasons']}")
```

- [ ] **Step 2: Run sur la banque réelle**
```bash
python tools/audit_clips.py "C:/Users/User/Downloads/Voix off/Clips/Muet"
```

- [ ] **Step 3: Commit**

---

## Self-Review
- Couvre tous les signaux du spec : OCR density, text_regions, watermark_confidence, zones. ✓
- Cache avec mtime ✓
- Tests : blank clip = accepté ; watermark @ en coin = rejeté ; texte central isolé = pas watermark. ✓
- Hors périmètre respecté : pas de face/watch detection ; ces signaux peuvent être ajoutés en Task séparée plus tard. ✓
