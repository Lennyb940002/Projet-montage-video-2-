# ✨ Boost Hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Un interrupteur ✨ Boost Hook qui ajoute au montage : cuts rapides + zoom punch sur le hook, zoom léger (Ken Burns) partout, flash + impact au début, whoosh sur les cuts (SFX depuis un dossier fourni).

**Architecture:** Extension du moteur `montage.render` avec un mode `boost`. Un nouveau module `sfx.py` pioche les effets sonores. Le mix audio (voix + SFX) et les effets vidéo (zoompan, flash) sont ajoutés au filtre ffmpeg existant. Booléen `boost` propagé service → server → UI.

**Tech Stack:** Python, ffmpeg (zoompan, drawbox, adelay, amix), Electron/JS.

---

## File Structure
- `backend/config.py` — ajout `SFX_DIR`, `BOOST` (réglages).
- `backend/pipeline/sfx.py` — **nouveau** : sélection de SFX par catégorie.
- `backend/pipeline/montage.py` — `apply_boost_cuts()` + `render(..., boost, sfx_dir)`.
- `backend/service.py` / `backend/server.py` — propagation `boost`.
- `frontend/` — interrupteur Boost + param dans preload/renderer.

---

## Task 1: Réglages config

**Files:** Modify `backend/config.py`

- [ ] **Step 1: Ajouter les réglages à la fin de `backend/config.py`**

```python
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(PROJECT_ROOT, "SFX")

BOOST = dict(
    hook_dur=3.5,     # durée du hook (s)
    hook_cut=0.8,     # longueur d'un cut dans le hook (s)
    sfx_volume=0.7,   # volume des SFX dans le mix
    flash=0.12,       # durée du flash blanc (s)
    zoom_rate=0.0010, # vitesse du zoom Ken Burns
    punch_rate=0.0030,# vitesse du zoom sur le 1er clip (punch)
    zoom_max=1.25,    # zoom maxi
)
```

- [ ] **Step 2: Commit**
```bash
git add backend/config.py
git commit -m "feat(boost): config (SFX_DIR, BOOST settings)"
```

---

## Task 2: Module sfx

**Files:** Create `backend/pipeline/sfx.py`, Test `backend/tests/test_sfx.py`

- [ ] **Step 1: Écrire le test (échec attendu)**
```python
# backend/tests/test_sfx.py
from backend.pipeline import sfx

def test_pick_matches_category(tmp_path):
    (tmp_path / "impact_boom.wav").write_bytes(b"x")
    (tmp_path / "whoosh1.mp3").write_bytes(b"x")
    assert sfx.pick("impact", str(tmp_path)).endswith("impact_boom.wav")
    assert sfx.pick("whoosh", str(tmp_path)).endswith("whoosh1.mp3")

def test_pick_none_when_absent(tmp_path):
    assert sfx.pick("riser", str(tmp_path)) is None

def test_list_sfx_empty_dir(tmp_path):
    assert sfx.list_sfx(str(tmp_path / "nope")) == []
```

- [ ] **Step 2: Lancer (échec)**
Run: `pytest backend/tests/test_sfx.py -v` — Expected: FAIL (import).

- [ ] **Step 3: Écrire `backend/pipeline/sfx.py`**
```python
import os, glob, random
from backend.config import SFX_DIR

def list_sfx(sfx_dir=SFX_DIR):
    if not os.path.isdir(sfx_dir):
        return []
    files = []
    for ext in ("*.wav", "*.mp3"):
        files += glob.glob(os.path.join(sfx_dir, ext))
    return sorted(files)

def pick(category, sfx_dir=SFX_DIR):
    cat = category.lower()
    cands = [f for f in list_sfx(sfx_dir) if cat in os.path.basename(f).lower()]
    return random.choice(cands) if cands else None
```

- [ ] **Step 4: Lancer (succès)** — Run: `pytest backend/tests/test_sfx.py -v` — Expected: PASS (3).

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/sfx.py backend/tests/test_sfx.py
git commit -m "feat(boost): sfx picker module"
```

---

## Task 3: Redécoupage du hook

**Files:** Modify `backend/pipeline/montage.py`, Test `backend/tests/test_montage.py`

- [ ] **Step 1: Ajouter le test dans `backend/tests/test_montage.py`**
```python
def test_apply_boost_cuts_subdivides_hook():
    from backend.pipeline.montage import apply_boost_cuts
    out = apply_boost_cuts([(0.0, 5.0)], hook_dur=3.5, hook_cut=0.8)
    assert len(out) > 1                      # plus de segments
    assert out[0] == (0.0, 0.8)
    assert abs(out[-1][1] - 5.0) < 1e-6      # couvre toujours jusqu'à la fin
    assert out[-1][0] == 3.5                 # dernier segment = reste après hook
```

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_montage.py::test_apply_boost_cuts_subdivides_hook -v` — FAIL.

- [ ] **Step 3: Ajouter `apply_boost_cuts` dans `montage.py` (après `sentence_ranges`)**
```python
def apply_boost_cuts(ranges, hook_dur, hook_cut):
    """Redécoupe la portion [0, hook_dur] en tranches de hook_cut (cuts rapides)."""
    out = []
    for s, e in ranges:
        if s >= hook_dur:
            out.append((s, e)); continue
        hook_end = min(e, hook_dur)
        t = s
        while t < hook_end - 1e-3:
            nt = min(t + hook_cut, hook_end)
            out.append((t, nt)); t = nt
        if e > hook_dur:
            out.append((hook_dur, e))
    return out
```

- [ ] **Step 4: Lancer (succès)** — PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/montage.py backend/tests/test_montage.py
git commit -m "feat(boost): hook re-segmentation (faster cuts)"
```

---

## Task 4: Rendu en mode boost (vidéo + SFX)

**Files:** Modify `backend/pipeline/montage.py`, Test `backend/tests/test_montage.py`

- [ ] **Step 1: Ajouter les tests**
```python
def test_render_boost_no_sfx(sample_audio, tmp_path):
    from backend.pipeline.montage import render
    from backend import ffmpeg
    ass = str(tmp_path / "s.ass")
    open(ass, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,80,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,4,0,5,80,80,80,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,TEST\n")
    dur = ffmpeg.probe_duration(sample_audio)
    out = str(tmp_path / "boost.mp4")
    render(sample_audio, ass, [(0.0, dur)], out, boost=True, sfx_dir=str(tmp_path / "empty"))
    import os
    assert os.path.exists(out)
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height", "-of", "csv=p=0", out])
    assert "1080,1920" in r.stdout

def test_render_boost_with_sfx(sample_audio, tmp_path):
    from backend.pipeline.montage import render
    from backend import ffmpeg
    import os
    sfxdir = tmp_path / "sfx"; sfxdir.mkdir()
    # génère 2 petits SFX réels (0.3 s) avec ffmpeg
    for name in ("impact_a.wav", "whoosh_a.wav"):
        ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=0.3",
                    str(sfxdir / name)])
    ass = str(tmp_path / "s2.ass")
    open(ass, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,80,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,1,0,0,0,100,100,0,0,1,4,0,5,80,80,80,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,TEST\n")
    dur = ffmpeg.probe_duration(sample_audio)
    out = str(tmp_path / "boost2.mp4")
    render(sample_audio, ass, [(0.0, dur*0.5), (dur*0.5, dur)], out, boost=True, sfx_dir=str(sfxdir))
    assert os.path.exists(out)
    # une piste audio est présente
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "error", "-select_streams", "a",
                    "-show_entries", "stream=codec_type", "-of", "csv=p=0", out])
    assert "audio" in r.stdout
```

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_montage.py -k boost -v` — FAIL (render n'a pas `boost`).

- [ ] **Step 3: Remplacer la fonction `render` dans `montage.py`**
```python
def render(audio_path, ass_path, ranges, out_path, clips_dir=DEFAULT_CLIPS_DIR,
           boost=False, sfx_dir=None):
    from backend.config import BOOST, SFX_DIR
    from backend.pipeline import sfx as sfxmod
    if sfx_dir is None:
        sfx_dir = SFX_DIR
    if boost:
        ranges = apply_boost_cuts(ranges, BOOST["hook_dur"], BOOST["hook_cut"])
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
    Ncl = len(chosen)

    # évènements SFX
    events = []
    if boost:
        imp = sfxmod.pick("impact", sfx_dir)
        if imp: events.append((0.0, imp))
        tcum = 0.0
        for idx, (s, e) in enumerate(ranges):
            if idx > 0:
                wh = sfxmod.pick("whoosh", sfx_dir)
                if wh: events.append((tcum, wh))
            tcum += (e - s)
    for (_t, f) in events:
        cmd += ["-i", f]

    # vidéo
    fc = []
    for k in range(Ncl):
        s = f"[{k}:v]scale={zw}:{zh}:force_original_aspect_ratio=increase,crop={W}:{H}"
        if boost:
            rate = BOOST["punch_rate"] if k == 0 else BOOST["zoom_rate"]
            s += (f",zoompan=z='min(zoom+{rate},{BOOST['zoom_max']})':d=1:"
                  f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
        s += f",setsar=1,fps={FPS},format=yuv420p[v{k}]"
        fc.append(s)
    fc.append("".join(f"[v{k}]" for k in range(Ncl)) + f"concat=n={Ncl}:v=1:a=0[cv]")
    ass_dir = os.path.dirname(os.path.abspath(ass_path))
    ass_name = os.path.basename(ass_path)
    if boost:
        fc.append(f"[cv]drawbox=x=0:y=0:w=iw:h=ih:color=white@1:t=fill:"
                  f"enable='lt(t,{BOOST['flash']})'[cf];[cf]ass={ass_name}[vout]")
    else:
        fc.append(f"[cv]ass={ass_name}[vout]")

    # audio
    if events:
        vol = BOOST["sfx_volume"]
        fc.append(f"[{Ncl}:a]aformat=sample_fmts=fltp:channel_layouts=stereo[av]")
        for i, (t, f) in enumerate(events):
            d = int(round(t * 1000))
            fc.append(f"[{Ncl + 1 + i}:a]adelay={d}|{d},volume={vol},"
                      f"aformat=sample_fmts=fltp:channel_layouts=stereo[se{i}]")
        mix = "[av]" + "".join(f"[se{i}]" for i in range(len(events)))
        fc.append(f"{mix}amix=inputs={len(events) + 1}:normalize=0:duration=first[aout]")
        amap = "[aout]"
    else:
        amap = f"{Ncl}:a"

    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", amap,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-r", str(FPS), "-shortest",
            "-movflags", "+faststart", "-map_metadata", "-1", os.path.abspath(out_path)]
    r = ffmpeg.run(cmd, cwd=ass_dir)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"Rendu échoué: {r.stderr[-400:]}")
    return out_path
```

- [ ] **Step 4: Lancer (succès)** — `pytest backend/tests/test_montage.py -k boost -v` — PASS (2). Puis toute la suite montage : `pytest backend/tests/test_montage.py -v`.

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/montage.py backend/tests/test_montage.py
git commit -m "feat(boost): render mode (zoom punch, ken burns, flash, sfx mix)"
```

---

## Task 5: Propagation service + server

**Files:** Modify `backend/service.py`, `backend/server.py`, Test `backend/tests/test_server.py`

- [ ] **Step 1: `make_video` accepte `boost`** — dans `backend/service.py`, remplacer la signature et l'appel render :
```python
def make_video(clean_path, text, out_path, style="karaoke_yellow", boost=False):
    """Aligne le texte sur l'audio nettoyé, génère sous-titres + vidéo."""
    words, duration = T.transcribe(clean_path)
    tokens, n_sent = align.tokenize(text)
    align.align(tokens, words)
    job = os.path.dirname(clean_path)
    ass = os.path.join(job, "subs.ass")
    subtitles.build_ass(tokens, n_sent, ass, style=style)
    ranges = montage.sentence_ranges(tokens, n_sent, duration)
    montage.render(clean_path, ass, ranges, out_path, boost=boost)
    return out_path
```

- [ ] **Step 2: `VideoReq` + endpoints** — dans `backend/server.py`, ajouter `boost` au modèle et le passer :
```python
class VideoReq(BaseModel):
    clean_path: str
    text: str
    out_path: str | None = None
    style: str = "karaoke_yellow"
    boost: bool = False
```
Et dans `/preview` et `/export`, remplacer les appels par :
```python
    return {"video_path": service.make_video(req.clean_path, req.text, out, req.style, req.boost)}
```
```python
    return {"video_path": service.make_video(req.clean_path, req.text, req.out_path, req.style, req.boost)}
```

- [ ] **Step 3: Test boost via l'API** — ajouter dans `backend/tests/test_server.py` :
```python
def test_preview_boost(sample_audio, tmp_path):
    data = client.post("/load", json={"audio_path": sample_audio}).json()
    out = str(tmp_path / "boost_api.mp4")
    r = client.post("/preview", json={"clean_path": data["clean_path"],
                                      "text": data["transcript"], "out_path": out, "boost": True})
    import os
    assert os.path.exists(r.json()["video_path"])
```

- [ ] **Step 4: Lancer** — `pytest backend/tests/test_server.py -v` — PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/service.py backend/server.py backend/tests/test_server.py
git commit -m "feat(boost): propagate boost flag through service + API"
```

---

## Task 6: Interrupteur Boost dans l'UI

**Files:** Modify `frontend/preload.js`, `frontend/index.html`, `frontend/styles.css`, `frontend/renderer.js`

- [ ] **Step 1: preload — passer `boost`** — remplacer les lignes preview/export dans `frontend/preload.js` :
```javascript
  preview: (clean_path, text, style, boost)           => post('/preview', { clean_path, text, style, boost }),
  export:  (clean_path, text, out_path, style, boost) => post('/export',  { clean_path, text, out_path, style, boost })
```

- [ ] **Step 2: index.html — l'interrupteur** — dans `.right`, avant `#genBtn` :
```html
        <label class="boost"><input type="checkbox" id="boost"> ✨ Boost Hook</label>
```

- [ ] **Step 3: styles.css — style de l'interrupteur** — ajouter :
```css
.boost { display:flex; align-items:center; gap:6px; font-size:13px; color:#ffd400; cursor:pointer; }
.boost input { accent-color:#ffd400; }
```

- [ ] **Step 4: renderer.js — lire l'état** — en haut, après `const styleSel = ...`, ajouter :
```javascript
const boostChk = document.getElementById('boost');
```
puis dans le handler `genBtn` remplacer l'appel preview par :
```javascript
    const res = await window.api.preview(state.cleanPath, transcript.value, styleSel.value, boostChk.checked);
```
et dans le handler `expBtn` remplacer l'appel export par :
```javascript
    const res = await window.api.export(state.cleanPath, transcript.value, out, styleSel.value, boostChk.checked);
```

- [ ] **Step 5: Vérifier la syntaxe**
Run: `cd frontend && for f in main.js preload.js renderer.js; do node --check "$f"; done`
Expected: aucune erreur.

- [ ] **Step 6: Commit**
```bash
git add frontend/preload.js frontend/index.html frontend/styles.css frontend/renderer.js
git commit -m "feat(boost): UI toggle for Boost Hook"
```

---

## Task 7: Dossier SFX + vérification finale

**Files:** Create `SFX/README.txt`

- [ ] **Step 1: Créer le dossier SFX avec une note**
```
SFX/README.txt :
Dépose ici tes effets sonores (.wav ou .mp3).
Nomme-les par catégorie : impact_xxx, whoosh_xxx, riser_xxx.
L'app pioche automatiquement dedans quand ✨ Boost Hook est activé.
Dossier vide = boost visuel seulement (pas de son ajouté).
```

- [ ] **Step 2: Lancer toute la suite** — `pytest backend/tests/ -v` — Expected: tous PASS.

- [ ] **Step 3: Test manuel** — `cd frontend && npm start` : cocher ✨ Boost Hook, déposer un audio, Générer → vérifier zoom/flash/cuts rapides au début (+ SFX si dossier rempli).

- [ ] **Step 4: Commit**
```bash
git add SFX/README.txt
git commit -m "chore(boost): SFX folder with instructions"
```

---

## Self-Review
- **Couverture spec :** SFX folder (T2,T7) · hook+global (T3,T4) · zoom punch + ken burns + flash + whoosh + impact (T4) · toggle UI (T6) · boost optionnel off par défaut (T5,T6) · dossier vide sans erreur (T2 `pick`→None, T4 test no_sfx). ✓
- **Types :** `render(..., boost, sfx_dir)`, `apply_boost_cuts(ranges, hook_dur, hook_cut)`, `sfx.pick(category, sfx_dir)`, `make_video(..., style, boost)` — cohérents entre tâches. ✓
- **Pas de placeholder.** ✓
