# AutoMontage — Phase 1 (MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Une app desktop Windows locale où l'on dépose un audio (voix IA) et qui produit une vidéo 9:16 sous-titrée, avec relecture/correction du texte avant export.

**Architecture:** Backend Python (modules pipeline + API FastAPI lancée en sidecar) ré-utilisant la logique de `C:\Users\User\Downloads\Voix off\_montage2.py`. Frontend Electron (HTML/JS) qui parle au backend via HTTP local (127.0.0.1). Phase 1 = drag-drop → transcription → silences auto → éditeur texte → aperçu → export. Pas encore de détection 🟡/🔴 ni d'éditeur audio (Phases 2-3).

**Tech Stack:** Python 3.13, faster-whisper (modèle `small`), ffmpeg (build Gyan déjà installé), FastAPI + uvicorn, pytest. Electron (Node.js), HTML/CSS/JS vanilla.

**Prérequis machine :** Python 3.13 (présent), ffmpeg (présent), **Node.js LTS à installer** (https://nodejs.org). Vérifier `node --version` et `npm --version` avant la Task 8.

**Constantes réutilisées (validées en production) :**
- ffmpeg/ffprobe : `C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin`
- Vidéo : 1080×1920, 30 fps, `libx264 -preset veryfast -crf 23 -pix_fmt yuv420p`, `aac 192k`, `+faststart`
- Zoom clips : `1.30` · Silences : keep `0.10 s`, seuil `-35dB` · Sous-titres : Arial Black 84, ≤3 mots/bloc, blanc→jaune (`\k`), Alignment 5

---

## File Structure

```
auto-montage/
├── backend/
│   ├── __init__.py
│   ├── config.py            # chemins ffmpeg, réglages par défaut
│   ├── ffmpeg.py            # localisation binaires + helpers run/probe
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── transcribe.py    # Word dataclass + transcribe()
│   │   ├── audio_clean.py   # remove_silences()
│   │   ├── align.py         # tokenize() + align()
│   │   ├── subtitles.py     # build_ass()
│   │   └── montage.py       # render()
│   ├── service.py           # orchestration: load_audio(), make_video()
│   ├── server.py            # FastAPI app
│   ├── requirements.txt
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py      # fixture sample.mp3
│       ├── fixtures/sample.mp3
│       ├── test_ffmpeg.py
│       ├── test_transcribe.py
│       ├── test_audio_clean.py
│       ├── test_align.py
│       ├── test_subtitles.py
│       ├── test_montage.py
│       └── test_server.py
└── frontend/
    ├── package.json
    ├── main.js              # process Electron + spawn backend
    ├── preload.js
    ├── index.html
    ├── styles.css
    └── renderer.js
```

---

## Task 0: Scaffold du backend

**Files:**
- Create: `backend/__init__.py`, `backend/pipeline/__init__.py`, `backend/tests/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/config.py`

- [ ] **Step 1: Créer l'arborescence et les `__init__.py` vides**

```bash
mkdir -p backend/pipeline backend/tests/fixtures frontend
```
Créer 3 fichiers vides : `backend/__init__.py`, `backend/pipeline/__init__.py`, `backend/tests/__init__.py`.

- [ ] **Step 2: Écrire `backend/requirements.txt`**

```
faster-whisper==1.2.1
fastapi==0.115.*
uvicorn==0.34.*
pytest==8.*
httpx==0.28.*
```

- [ ] **Step 3: Écrire `backend/config.py`**

```python
import os

FFMPEG_BIN = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"

# Banque de clips muets par défaut (modifiable depuis l'UI plus tard)
DEFAULT_CLIPS_DIR = r"C:\Users\User\Downloads\Voix off\Clips\Muet"

WHISPER_MODEL = "small"

VIDEO = dict(width=1080, height=1920, fps=30, zoom=1.30)
SILENCE = dict(keep=0.10, threshold="-35dB")
SUBS = dict(font="Arial Black", size=84, maxwords=3,
            yellow="&H0000FFFF&", white="&H00FFFFFF&")

WORKDIR = os.path.join(os.path.expanduser("~"), ".automontage", "work")
os.makedirs(WORKDIR, exist_ok=True)
```

- [ ] **Step 4: Installer les dépendances**

Run: `pip install -r backend/requirements.txt`
Expected: installation OK (faster-whisper déjà présent).

- [ ] **Step 5: Commit**

```bash
git add backend frontend
git commit -m "chore: scaffold backend structure and config"
```

---

## Task 1: Module ffmpeg (localisation + helpers)

**Files:**
- Create: `backend/ffmpeg.py`
- Test: `backend/tests/test_ffmpeg.py`
- Create fixture: `backend/tests/conftest.py`, `backend/tests/fixtures/sample.mp3`

- [ ] **Step 1: Créer la fixture audio**

Copier un court mp3 existant comme échantillon de test :
```bash
cp "C:/Users/User/Downloads/Voix off/Voici les trois montres que j'ai le plus vendu ces derniers mois.mp3" backend/tests/fixtures/sample.mp3
```

- [ ] **Step 2: Écrire `backend/tests/conftest.py`**

```python
import os, pytest

@pytest.fixture
def sample_audio():
    return os.path.join(os.path.dirname(__file__), "fixtures", "sample.mp3")
```

- [ ] **Step 3: Écrire le test (échec attendu)**

```python
# backend/tests/test_ffmpeg.py
import os
from backend import ffmpeg

def test_binaries_exist():
    assert os.path.exists(ffmpeg.FFMPEG)
    assert os.path.exists(ffmpeg.FFPROBE)

def test_probe_duration(sample_audio):
    d = ffmpeg.probe_duration(sample_audio)
    assert 5 < d < 30  # sample ~13 s
```

- [ ] **Step 4: Lancer le test pour vérifier l'échec**

Run: `pytest backend/tests/test_ffmpeg.py -v`
Expected: FAIL (`ModuleNotFoundError` / `AttributeError`).

- [ ] **Step 5: Écrire `backend/ffmpeg.py`**

```python
import os, subprocess
from backend.config import FFMPEG_BIN

FFMPEG = os.path.join(FFMPEG_BIN, "ffmpeg.exe")
FFPROBE = os.path.join(FFMPEG_BIN, "ffprobe.exe")

def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def probe_duration(path):
    r = run([FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", path])
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise RuntimeError(f"Durée illisible pour {path}: {r.stderr[-300:]}")
```

- [ ] **Step 6: Lancer le test (succès attendu)**

Run: `pytest backend/tests/test_ffmpeg.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/ffmpeg.py backend/tests/test_ffmpeg.py backend/tests/conftest.py backend/tests/fixtures/sample.mp3
git commit -m "feat: ffmpeg locator and probe_duration helper"
```

---

## Task 2: Module transcribe

**Files:**
- Create: `backend/pipeline/transcribe.py`
- Test: `backend/tests/test_transcribe.py`

- [ ] **Step 1: Écrire le test (échec attendu)**

```python
# backend/tests/test_transcribe.py
from backend.pipeline.transcribe import transcribe, Word

def test_transcribe_returns_words(sample_audio):
    words, duration = transcribe(sample_audio)
    assert duration > 5
    assert len(words) > 5
    assert isinstance(words[0], Word)
    assert all(w.start <= w.end for w in words)
    # mots couvrent globalement l'audio
    assert words[-1].end <= duration + 0.5
    # texte plausible
    joined = " ".join(w.text for w in words).lower()
    assert "montre" in joined
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `pytest backend/tests/test_transcribe.py -v`
Expected: FAIL (import error).

- [ ] **Step 3: Écrire `backend/pipeline/transcribe.py`**

```python
from dataclasses import dataclass
from faster_whisper import WhisperModel
from backend.config import WHISPER_MODEL

@dataclass
class Word:
    text: str
    start: float
    end: float
    prob: float

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model

def transcribe(audio_path):
    """Retourne (list[Word], duree). PAS d'initial_prompt (sinon Whisper
    ne renvoie qu'un segment - bug constaté)."""
    model = _get_model()
    segs, info = model.transcribe(audio_path, language="fr",
                                  beam_size=5, word_timestamps=True)
    words = []
    for s in segs:
        for w in (s.words or []):
            if w.word.strip():
                words.append(Word(w.word.strip(), w.start, w.end, w.probability))
    return words, info.duration
```

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `pytest backend/tests/test_transcribe.py -v`
Expected: PASS (lent ~10-20 s, téléchargement modèle la 1ère fois).

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/transcribe.py backend/tests/test_transcribe.py
git commit -m "feat: transcribe module (faster-whisper word timestamps)"
```

---

## Task 3: Module audio_clean (suppression des silences)

**Files:**
- Create: `backend/pipeline/audio_clean.py`
- Test: `backend/tests/test_audio_clean.py`

- [ ] **Step 1: Écrire le test (échec attendu)**

```python
# backend/tests/test_audio_clean.py
import os
from backend.pipeline.audio_clean import remove_silences
from backend import ffmpeg

def test_remove_silences_shortens(sample_audio, tmp_path):
    out = str(tmp_path / "clean.mp3")
    result = remove_silences(sample_audio, out)
    assert os.path.exists(result)
    before = ffmpeg.probe_duration(sample_audio)
    after = ffmpeg.probe_duration(result)
    assert after <= before          # jamais plus long
    assert after > before * 0.4     # mais pas vidé
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `pytest backend/tests/test_audio_clean.py -v`
Expected: FAIL (import error).

- [ ] **Step 3: Écrire `backend/pipeline/audio_clean.py`**

```python
from backend import ffmpeg
from backend.config import SILENCE

def remove_silences(audio_path, out_path):
    """Resserre les silences (keep max 0.10 s, seuil -35dB). Réversible côté
    appelant (on garde l'original)."""
    keep = SILENCE["keep"]; thr = SILENCE["threshold"]
    sr = (f"silenceremove=start_periods=1:start_duration=0:start_threshold={thr}:"
          f"stop_periods=-1:stop_duration={keep}:stop_threshold={thr}:detection=rms")
    r = ffmpeg.run([ffmpeg.FFMPEG, "-y", "-i", audio_path, "-af", sr,
                    "-c:a", "libmp3lame", "-q:a", "2", out_path])
    if r.returncode != 0:
        raise RuntimeError(f"silenceremove a échoué: {r.stderr[-300:]}")
    return out_path
```

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `pytest backend/tests/test_audio_clean.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/audio_clean.py backend/tests/test_audio_clean.py
git commit -m "feat: audio_clean silence removal"
```

---

## Task 4: Module align (tokenize + alignement texte↔mots)

**Files:**
- Create: `backend/pipeline/align.py`
- Test: `backend/tests/test_align.py`

- [ ] **Step 1: Écrire le test (échec attendu)**

```python
# backend/tests/test_align.py
from backend.pipeline.align import tokenize, align
from backend.pipeline.transcribe import Word

def test_tokenize_sentences_and_symbols():
    toks, n = tokenize("Salut le monde. 90 % des gens ?")
    assert n == 2  # deux phrases
    assert toks[0]["disp"].lower() == "salut"
    # le symbole % est fusionné au mot précédent, pas un token isolé
    assert any("%" in t["disp"] for t in toks)

def test_align_transfers_timings_exact_match():
    words = [Word("salut", 0.0, 0.5, 0.9), Word("monde", 0.5, 1.0, 0.9)]
    toks, n = tokenize("Salut monde.")
    align(toks, words)
    assert toks[0]["start"] == 0.0
    assert toks[1]["start"] == 0.5
    # monotonie
    assert toks[0]["start"] <= toks[1]["start"]

def test_align_interpolates_missing():
    # whisper n'a qu'un mot, le texte en a 3 -> interpolation, pas de None
    words = [Word("monde", 1.0, 1.4, 0.9)]
    toks, n = tokenize("salut le monde")
    align(toks, words)
    assert all(t["start"] is not None for t in toks)
    assert all(t["end"] >= t["start"] for t in toks)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `pytest backend/tests/test_align.py -v`
Expected: FAIL (import error).

- [ ] **Step 3: Écrire `backend/pipeline/align.py`**

```python
import re, difflib

def norm(w):
    return re.sub(r"[^0-9a-zàâäçéèêëîïôöùûüœæ]", "", w.lower())

def _clean(s):
    for ch in "«»“”\"":
        s = s.replace(ch, "")
    return s.strip()

def tokenize(text):
    """-> (tokens, n_sent). token = {disp, norm, sent, start, end}.
    Les symboles isolés (%, €, …) sont fusionnés au mot précédent."""
    sents = [p.strip() for p in re.split(r"(?<=[.!?…:])\s+", text.replace("\n", " ")) if p.strip()]
    tokens = []
    for si, sent in enumerate(sents):
        for raw in sent.split():
            n = norm(raw); disp = _clean(raw)
            if n == "":
                if disp and tokens:
                    tokens[-1]["disp"] += " " + disp
                continue
            tokens.append({"disp": disp, "norm": n, "sent": si,
                           "start": None, "end": None})
    return tokens, len(sents)

def align(tokens, words):
    """Transfère les timings des mots whisper sur les tokens du texte."""
    a = [t["norm"] for t in tokens]
    b = [norm(w.text) for w in words]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                tokens[i1 + k]["start"] = words[j1 + k].start
                tokens[i1 + k]["end"] = words[j1 + k].end
        elif tag == "replace" and j2 > j1:
            s = words[j1].start; e = words[j2 - 1].end; cnt = i2 - i1
            step = (e - s) / cnt if cnt else 0
            for k in range(cnt):
                tokens[i1 + k]["start"] = s + step * k
                tokens[i1 + k]["end"] = s + step * (k + 1)
    # interpolation des trous
    n = len(tokens); i = 0
    while i < n:
        if tokens[i]["start"] is None:
            j = i
            while j < n and tokens[j]["start"] is None:
                j += 1
            prev_e = tokens[i - 1]["end"] if i > 0 and tokens[i - 1]["end"] is not None else 0.0
            next_s = tokens[j]["start"] if j < n and tokens[j]["start"] is not None else prev_e + 0.4 * (j - i)
            cnt = j - i; step = (next_s - prev_e) / (cnt + 1)
            for k in range(cnt):
                tokens[i + k]["start"] = prev_e + step * (k + 1)
                tokens[i + k]["end"] = prev_e + step * (k + 2)
            i = j
        else:
            i += 1
    # monotonie
    last = 0.0
    for t in tokens:
        if t["start"] < last: t["start"] = last
        if t["end"] <= t["start"]: t["end"] = t["start"] + 0.08
        last = t["end"]
    return tokens
```

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `pytest backend/tests/test_align.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/align.py backend/tests/test_align.py
git commit -m "feat: align module (tokenize + difflib timing transfer)"
```

---

## Task 5: Module subtitles (génération .ass karaoké)

**Files:**
- Create: `backend/pipeline/subtitles.py`
- Test: `backend/tests/test_subtitles.py`

- [ ] **Step 1: Écrire le test (échec attendu)**

```python
# backend/tests/test_subtitles.py
from backend.pipeline.subtitles import build_ass, ass_time

def test_ass_time_format():
    assert ass_time(0) == "0:00:00.00"
    assert ass_time(61.5) == "0:01:01.50"

def test_build_ass(tmp_path):
    tokens = [
        {"disp": "Salut", "sent": 0, "start": 0.0, "end": 0.4},
        {"disp": "le", "sent": 0, "start": 0.4, "end": 0.6},
        {"disp": "monde", "sent": 0, "start": 0.6, "end": 1.0},
    ]
    out = str(tmp_path / "s.ass")
    build_ass(tokens, 1, out)
    content = open(out, encoding="utf-8").read()
    # en-tête AVEC champ Name (sinon bug virgule)
    assert "Format: Layer, Start, End, Style, Name," in content
    # karaoké \k présent et texte en MAJUSCULES
    assert "\\k" in content and "SALUT" in content
    # pas de double Dialogue par mot : 1 ligne par bloc
    assert content.count("Dialogue:") == 1
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `pytest backend/tests/test_subtitles.py -v`
Expected: FAIL (import error).

- [ ] **Step 3: Écrire `backend/pipeline/subtitles.py`**

```python
from backend.config import VIDEO, SUBS

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{fs},{yellow},{white},&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,5,2,5,80,80,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def ass_time(sec):
    if sec < 0: sec = 0
    cs = int(round(sec * 100)); h = cs // 360000; cs %= 360000
    m = cs // 6000; cs %= 6000; s = cs // 100; c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"

def build_ass(tokens, n_sent, path):
    mw = SUBS["maxwords"]
    lines = [HEADER.format(w=VIDEO["width"], h=VIDEO["height"], font=SUBS["font"],
                           fs=SUBS["size"], yellow=SUBS["yellow"], white=SUBS["white"])]
    chunks = []
    for si in range(n_sent):
        ws = [t for t in tokens if t["sent"] == si]
        for c in range(0, len(ws), mw):
            chunks.append(ws[c:c + mw])
    for ci, chunk in enumerate(chunks):
        start = chunk[0]["start"]
        end = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else chunk[-1]["end"] + 0.3
        if end <= start: end = start + 0.1
        n = len(chunk); parts = []
        for j in range(n):
            if j < n - 1:
                k = int(round((chunk[j + 1]["start"] - chunk[j]["start"]) * 100))
            else:
                k = int(round((chunk[j]["end"] - chunk[j]["start"]) * 100))
            if k < 1: k = 1
            parts.append("{\\k%d}%s" % (k, chunk[j]["disp"].upper()))
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,80,80,80,, " + " ".join(parts))
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path
```

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `pytest backend/tests/test_subtitles.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/subtitles.py backend/tests/test_subtitles.py
git commit -m "feat: subtitles module (karaoke ASS)"
```

---

## Task 6: Module montage (sélection clips + rendu)

**Files:**
- Create: `backend/pipeline/montage.py`
- Test: `backend/tests/test_montage.py`

- [ ] **Step 1: Écrire le test (échec attendu)**

```python
# backend/tests/test_montage.py
import os
from backend.pipeline.montage import list_clips, sentence_ranges, render
from backend import ffmpeg
from backend.config import DEFAULT_CLIPS_DIR

def test_sentence_ranges_cover_duration():
    tokens = [
        {"sent": 0, "start": 0.0, "end": 1.0},
        {"sent": 1, "start": 1.0, "end": 2.0},
    ]
    ranges = sentence_ranges(tokens, 2, 3.0)
    assert ranges[0][0] == 0.0
    assert ranges[-1][1] == 3.0

def test_list_clips_dedup():
    clips = list_clips(DEFAULT_CLIPS_DIR)
    assert len(clips) > 0

def test_render_makes_vertical_video(sample_audio, tmp_path):
    # mini sous-titre + 1 phrase
    ass = str(tmp_path / "s.ass")
    open(ass, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,80,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,4,0,5,80,80,80,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,80,80,80,,TEST\n")
    dur = ffmpeg.probe_duration(sample_audio)
    ranges = [(0.0, dur)]
    out = str(tmp_path / "out.mp4")
    render(sample_audio, ass, ranges, out)
    assert os.path.exists(out)
    # vérifie dimensions verticales
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height", "-of", "csv=p=0", out])
    assert "1080,1920" in r.stdout
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `pytest backend/tests/test_montage.py -v`
Expected: FAIL (import error).

- [ ] **Step 3: Écrire `backend/pipeline/montage.py`**

```python
import os, glob, random
from backend import ffmpeg
from backend.config import VIDEO, DEFAULT_CLIPS_DIR

def list_clips(clips_dir=DEFAULT_CLIPS_DIR):
    """Clips .mp4 dédoublonnés par taille de fichier."""
    seen = {}; clips = []
    for c in sorted(glob.glob(os.path.join(clips_dir, "*.mp4"))):
        sz = os.path.getsize(c)
        if sz in seen: continue
        seen[sz] = c; clips.append(c)
    return clips

def sentence_ranges(tokens, n_sent, duration):
    starts = []
    for si in range(n_sent):
        ws = [t for t in tokens if t["sent"] == si]
        starts.append(ws[0]["start"] if ws else (starts[-1] if starts else 0.0))
    if starts: starts[0] = 0.0
    ranges = []
    for si in range(n_sent):
        s = starts[si]; e = starts[si + 1] if si + 1 < n_sent else duration
        ranges.append((s, max(e, s + 0.3)))
    return ranges or [(0.0, duration)]

def _pick_clips(ranges, clips):
    durs = {c: ffmpeg.probe_duration(c) for c in clips}
    avail = clips[:]; random.shuffle(avail); chosen = []
    for (s, e) in ranges:
        L = e - s; pick = None
        for n, c in enumerate(avail):
            if durs[c] >= L + 0.15:
                pick = avail.pop(n); break
        if pick is not None:
            off = random.uniform(0, max(0.0, durs[pick] - L))
            chosen.append((pick, off, L, False))
        elif avail:
            c = max(avail, key=lambda x: durs[x]); avail.remove(c)
            chosen.append((c, 0.0, L, True))
        else:
            avail = clips[:]; random.shuffle(avail); c = avail.pop(0)
            chosen.append((c, 0.0, L, durs[c] < L + 0.15))
    return chosen

def render(audio_path, ass_path, ranges, out_path, clips_dir=DEFAULT_CLIPS_DIR):
    clips = list_clips(clips_dir)
    if not clips:
        raise RuntimeError(f"Aucun clip dans {clips_dir}")
    chosen = _pick_clips(ranges, clips)
    W, H, FPS, ZOOM = VIDEO["width"], VIDEO["height"], VIDEO["fps"], VIDEO["zoom"]
    zw, zh = int(W * ZOOM), int(H * ZOOM)
    cmd = [ffmpeg.FFMPEG, "-y"]
    for (c, off, L, loop) in chosen:
        if loop: cmd += ["-stream_loop", "-1", "-t", f"{L:.3f}", "-i", c]
        else: cmd += ["-ss", f"{off:.3f}", "-t", f"{L:.3f}", "-i", c]
    cmd += ["-i", audio_path]
    N = len(chosen); fc = []
    for k in range(N):
        fc.append(f"[{k}:v]scale={zw}:{zh}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{H},setsar=1,fps={FPS},format=yuv420p[v{k}]")
    fc.append("".join(f"[v{k}]" for k in range(N)) + f"concat=n={N}:v=1:a=0[cv]")
    # chemin .ass relatif (exécution depuis son dossier) pour éviter l'échappement Windows
    ass_dir = os.path.dirname(os.path.abspath(ass_path))
    ass_name = os.path.basename(ass_path)
    fc.append(f"[cv]ass={ass_name}[vout]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{N}:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-r", str(FPS), "-shortest",
            "-movflags", "+faststart", "-map_metadata", "-1", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=ass_dir)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"Rendu échoué: {r.stderr[-400:]}")
    return out_path
```

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `pytest backend/tests/test_montage.py -v`
Expected: PASS (3 tests, le rendu prend quelques secondes).

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/montage.py backend/tests/test_montage.py
git commit -m "feat: montage module (random clips + ffmpeg render)"
```

---

## Task 7: Service d'orchestration + serveur FastAPI

**Files:**
- Create: `backend/service.py`
- Create: `backend/server.py`
- Test: `backend/tests/test_server.py`

- [ ] **Step 1: Écrire `backend/service.py`**

```python
import os, uuid
from backend.config import WORKDIR
from backend.pipeline import transcribe as T
from backend.pipeline import audio_clean, align, subtitles, montage

def load_audio(audio_path):
    """Transcrit + nettoie les silences. Retourne dict {clean_path, transcript, duration}."""
    job = os.path.join(WORKDIR, uuid.uuid4().hex)
    os.makedirs(job, exist_ok=True)
    clean = os.path.join(job, "clean.mp3")
    audio_clean.remove_silences(audio_path, clean)
    words, duration = T.transcribe(clean)
    transcript = " ".join(w.text for w in words)
    return {"job": job, "clean_path": clean, "transcript": transcript,
            "duration": duration}

def make_video(clean_path, text, out_path):
    """Aligne le texte (corrigé) sur l'audio nettoyé, génère sous-titres + vidéo."""
    words, duration = T.transcribe(clean_path)
    tokens, n_sent = align.tokenize(text)
    align.align(tokens, words)
    job = os.path.dirname(clean_path)
    ass = os.path.join(job, "subs.ass")
    subtitles.build_ass(tokens, n_sent, ass)
    ranges = montage.sentence_ranges(tokens, n_sent, duration)
    montage.render(clean_path, ass, ranges, out_path)
    return out_path
```

- [ ] **Step 2: Écrire le test serveur (échec attendu)**

```python
# backend/tests/test_server.py
import os
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_load_and_preview(sample_audio, tmp_path):
    r = client.post("/load", json={"audio_path": sample_audio})
    data = r.json()
    assert "montre" in data["transcript"].lower()
    assert data["duration"] > 5
    out = str(tmp_path / "preview.mp4")
    r2 = client.post("/preview", json={"clean_path": data["clean_path"],
                                       "text": data["transcript"], "out_path": out})
    assert os.path.exists(r2.json()["video_path"])
```

- [ ] **Step 3: Lancer le test pour vérifier l'échec**

Run: `pytest backend/tests/test_server.py -v`
Expected: FAIL (import error).

- [ ] **Step 4: Écrire `backend/server.py`**

```python
import os, uuid
from fastapi import FastAPI
from pydantic import BaseModel
from backend import service
from backend.config import WORKDIR

app = FastAPI(title="AutoMontage")

class LoadReq(BaseModel):
    audio_path: str

class VideoReq(BaseModel):
    clean_path: str
    text: str
    out_path: str | None = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/load")
def load(req: LoadReq):
    return service.load_audio(req.audio_path)

@app.post("/preview")
def preview(req: VideoReq):
    out = req.out_path or os.path.join(WORKDIR, uuid.uuid4().hex + ".mp4")
    return {"video_path": service.make_video(req.clean_path, req.text, out)}

@app.post("/export")
def export(req: VideoReq):
    return {"video_path": service.make_video(req.clean_path, req.text, req.out_path)}
```

- [ ] **Step 5: Lancer le test (succès attendu)**

Run: `pytest backend/tests/test_server.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Vérifier le lancement manuel du serveur**

Run: `python -m uvicorn backend.server:app --host 127.0.0.1 --port 8765`
Expected: démarre ; `http://127.0.0.1:8765/health` renvoie `{"status":"ok"}`. Arrêter avec Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add backend/service.py backend/server.py backend/tests/test_server.py
git commit -m "feat: orchestration service + FastAPI endpoints"
```

---

## Task 8: Scaffold Electron + lancement du backend en sidecar

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/main.js`
- Create: `frontend/preload.js`

- [ ] **Step 1: Vérifier Node.js**

Run: `node --version && npm --version`
Expected: versions affichées. Sinon installer Node.js LTS d'abord.

- [ ] **Step 2: Écrire `frontend/package.json`**

```json
{
  "name": "automontage",
  "version": "0.1.0",
  "main": "main.js",
  "scripts": { "start": "electron ." },
  "devDependencies": { "electron": "^33.0.0" }
}
```

- [ ] **Step 3: Installer Electron**

Run: `cd frontend && npm install`
Expected: `node_modules/` créé (ignoré par git).

- [ ] **Step 4: Écrire `frontend/main.js`**

```javascript
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let backend;
const PORT = 8765;

function startBackend() {
  // lance: python -m uvicorn backend.server:app  (cwd = racine projet)
  const root = path.join(__dirname, '..');
  backend = spawn('python', ['-m', 'uvicorn', 'backend.server:app',
    '--host', '127.0.0.1', '--port', String(PORT)],
    { cwd: root, shell: true });
  backend.stdout.on('data', d => console.log('[py]', d.toString()));
  backend.stderr.on('data', d => console.log('[py]', d.toString()));
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1400, height: 900, backgroundColor: '#0f0f10',
    webPreferences: { preload: path.join(__dirname, 'preload.js') }
  });
  win.loadFile('index.html');
}

app.whenReady().then(() => {
  startBackend();
  // petit délai pour laisser le serveur démarrer
  setTimeout(createWindow, 1500);
});

app.on('window-all-closed', () => {
  if (backend) backend.kill();
  if (process.platform !== 'darwin') app.quit();
});
```

- [ ] **Step 5: Écrire `frontend/preload.js`**

```javascript
const { contextBridge } = require('electron');
const PORT = 8765;
const base = `http://127.0.0.1:${PORT}`;

contextBridge.exposeInMainWorld('api', {
  load:    (audio_path)        => fetch(`${base}/load`,    { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ audio_path }) }).then(r=>r.json()),
  preview: (clean_path, text)  => fetch(`${base}/preview`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ clean_path, text }) }).then(r=>r.json()),
  export:  (clean_path, text, out_path) => fetch(`${base}/export`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ clean_path, text, out_path }) }).then(r=>r.json())
});
```

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/main.js frontend/preload.js
git commit -m "feat: electron scaffold + python sidecar launch"
```

---

## Task 9: Interface (HTML + CSS, layout validé)

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/styles.css`

- [ ] **Step 1: Écrire `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><link rel="stylesheet" href="styles.css"></head>
<body>
  <div class="app">
    <div class="top">
      <span class="logo">⏱ AutoMontage</span>
      <span id="file" class="file">Dépose un audio…</span>
      <div class="right">
        <button id="genBtn" class="btn green" disabled>🎬 Générer l'aperçu</button>
        <button id="expBtn" class="btn primary" disabled>⬇ Exporter</button>
      </div>
    </div>
    <div class="mid">
      <div id="drop" class="center">
        <div class="dropzone">📥 Glisse ton fichier audio ici</div>
        <video id="preview" controls style="display:none"></video>
        <div id="status" class="status"></div>
      </div>
      <div class="panel right">
        <div class="ttl">Transcription (corrigeable)</div>
        <textarea id="transcript" placeholder="La transcription apparaîtra ici…"></textarea>
      </div>
    </div>
  </div>
  <script src="renderer.js"></script>
</body>
</html>
```

- [ ] **Step 2: Écrire `frontend/styles.css`**

```css
* { box-sizing:border-box; margin:0; padding:0; font-family:'Segoe UI',sans-serif; }
body { background:#0f0f10; color:#e8e8ea; height:100vh; overflow:hidden; }
.app { display:grid; grid-template-rows:46px 1fr; height:100vh; }
.top { display:flex; align-items:center; gap:14px; padding:0 14px; background:#181819; border-bottom:1px solid #000; }
.logo { font-weight:700; color:#4ad7d1; }
.file { color:#9a9aa0; font-size:13px; }
.top .right { margin-left:auto; display:flex; gap:10px; }
.btn { background:#2a2a2d; border:1px solid #3a3a3f; color:#e8e8ea; padding:7px 14px; border-radius:7px; font-size:13px; cursor:pointer; }
.btn:disabled { opacity:.4; cursor:default; }
.btn.primary { background:#3b82f6; border-color:#3b82f6; color:#fff; }
.btn.green { background:#10b981; border-color:#10b981; color:#fff; }
.mid { display:grid; grid-template-columns:1fr 380px; min-height:0; }
.center { display:flex; flex-direction:column; align-items:center; justify-content:center; background:#0b0b0c; gap:14px; }
.dropzone { border:2px dashed #3a3a3f; border-radius:14px; padding:60px 40px; color:#888; }
.center.drag .dropzone { border-color:#4ad7d1; color:#4ad7d1; }
#preview { width:240px; aspect-ratio:9/16; background:#000; border-radius:12px; }
.status { font-size:13px; color:#9a9aa0; min-height:18px; }
.panel.right { border-left:1px solid #000; background:#161617; padding:12px; display:flex; flex-direction:column; }
.ttl { font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#7a7a80; margin-bottom:10px; }
#transcript { flex:1; background:#0f0f10; color:#dcdce0; border:1px solid #2a2a2d; border-radius:8px; padding:12px; font-size:15px; line-height:1.9; resize:none; }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html frontend/styles.css
git commit -m "feat: UI layout (drag-drop + transcript editor)"
```

---

## Task 10: Logique UI (renderer.js)

**Files:**
- Create: `frontend/renderer.js`

- [ ] **Step 1: Écrire `frontend/renderer.js`**

```javascript
const drop = document.getElementById('drop');
const fileLbl = document.getElementById('file');
const status = document.getElementById('status');
const transcript = document.getElementById('transcript');
const preview = document.getElementById('preview');
const genBtn = document.getElementById('genBtn');
const expBtn = document.getElementById('expBtn');

let cleanPath = null;

['dragenter','dragover'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.add('drag');
}));
['dragleave','drop'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.remove('drag');
}));

drop.addEventListener('drop', async ev => {
  const f = ev.dataTransfer.files[0];
  if (!f) return;
  fileLbl.textContent = f.name;
  status.textContent = 'Transcription + nettoyage en cours…';
  genBtn.disabled = expBtn.disabled = true;
  try {
    const res = await window.api.load(f.path);
    cleanPath = res.clean_path;
    transcript.value = res.transcript;
    status.textContent = `Prêt (${res.duration.toFixed(1)} s). Corrige le texte puis génère.`;
    genBtn.disabled = false;
  } catch (e) {
    status.textContent = 'Erreur : ' + e;
  }
});

genBtn.addEventListener('click', async () => {
  status.textContent = 'Génération de l\'aperçu…';
  try {
    const res = await window.api.preview(cleanPath, transcript.value);
    preview.src = 'file://' + res.video_path.replace(/\\/g,'/');
    preview.style.display = 'block';
    status.textContent = 'Aperçu prêt.';
    expBtn.disabled = false;
  } catch (e) { status.textContent = 'Erreur : ' + e; }
});

expBtn.addEventListener('click', async () => {
  const out = prompt('Chemin de sortie (ex: C:\\Users\\User\\Desktop\\video.mp4)');
  if (!out) return;
  status.textContent = 'Export…';
  try {
    const res = await window.api.export(cleanPath, transcript.value, out);
    status.textContent = 'Exporté : ' + res.video_path;
  } catch (e) { status.textContent = 'Erreur : ' + e; }
});
```

- [ ] **Step 2: Test manuel de bout en bout**

Run: `cd frontend && npm start`
Vérifier dans l'app :
1. La fenêtre s'ouvre (fond sombre, zone de dépôt).
2. Glisser un mp3 (ex. `C:\Users\User\Downloads\Voix off\Voici les trois montres...mp3`).
3. Le texte transcrit apparaît à droite après ~10-20 s ; statut « Prêt ».
4. Corriger un mot (ex. une marque), cliquer **Générer l'aperçu** → la vidéo 9:16 s'affiche et se lit avec sous-titres karaoké.
5. **Exporter** → saisir un chemin `.mp4` → fichier créé et lisible.

Expected: chaque étape OK. Noter tout écart.

- [ ] **Step 3: Commit**

```bash
git add frontend/renderer.js
git commit -m "feat: renderer logic (drop -> transcript -> preview -> export)"
```

---

## Task 11: Vérification finale & README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Lancer toute la suite de tests backend**

Run: `pytest backend/tests/ -v`
Expected: tous PASS.

- [ ] **Step 2: Écrire `README.md`**

```markdown
# AutoMontage (Phase 1 / MVP)

App locale de montage vidéo automatisé : audio (voix IA) → vidéo 9:16 sous-titrée.

## Prérequis
- Python 3.13 + `pip install -r backend/requirements.txt`
- ffmpeg (build Gyan, chemin dans `backend/config.py`)
- Node.js LTS

## Lancer
```
cd frontend
npm install
npm start
```

## Workflow
Glisser un audio → transcription + silences auto → corriger le texte → Générer l'aperçu → Exporter.

## Tests
`pytest backend/tests/ -v`

## Réglages
Voir `backend/config.py` (modèle Whisper, format, zoom, silences, banque de clips).
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README for Phase 1 MVP"
```

---

## Notes pour les phases suivantes (hors Phase 1)

- **Phase 2** : module `detect.py` (🟡 reprises via `find_retakes`, 🔴 mots `prob < seuil ~0.5`), endpoints `/detect`, coupe audio + re-alignement, UI surlignage cliquable (passer le `<textarea>` à un éditeur riche `contenteditable`).
- **Phase 3** : wavesurfer.js dans le panneau bas, sélection/coupe/pré-écoute, endpoint `/cut`.
- **Phase 4** : gestion banque de clips (exclusion), réglages persistants, Annuler/Refaire.
```
