# Pack Dynamisme — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Rendre les vidéos « montées par un humain » : emphase des sous-titres (mot-clé qui pop), motion animé (Ken Burns + punch + shake), transitions length-preserving — sur une base extensible (keywords + director).

**Architecture:** `keywords.py` (mots à forte valeur, source unique) + `director.py` (timeline de décisions motion/transitions) consommés par `subtitles.py` (style premium) et `montage.render(plan=...)`. Rétro-compatible.

**Tech Stack:** Python, ffmpeg (ASS `\t`/`\fscx`, zoompan, crop x/y, fade), pytest.

---

## Task 1: keywords.py (source unique des mots à forte valeur)

**Files:** Create `backend/pipeline/keywords.py`, Test `backend/tests/test_keywords.py`

- [ ] **Step 1: Test (échec)**
```python
# backend/tests/test_keywords.py
from backend.pipeline import keywords

def _toks(words):
    return [{"disp": w, "start": i*0.4, "end": i*0.4+0.3, "sent": 0} for i, w in enumerate(words)]

def test_mark_flags_keywords():
    toks = keywords.mark(_toks(["Cette", "Rolex", "à", "200€", "est", "incroyable", "la"]))
    flags = {t["disp"]: t["kw"] for t in toks}
    assert flags["Rolex"] and flags["200€"] and flags["incroyable"]
    assert not flags["Cette"] and not flags["la"]
```

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_keywords.py -v` → FAIL.

- [ ] **Step 3: Écrire `backend/pipeline/keywords.py`**
```python
from backend.pipeline.sfx_plan import (is_price, is_number, is_watch_brand,
                                       is_question_word, is_cta, _norm)

SUPERLATIVES = {"incroyable", "jamais", "fou", "folle", "énorme", "dingue", "ouf",
                "record", "exceptionnel", "rare", "unique", "meilleur", "luxe",
                "premium", "gratuit", "exclusif", "magnifique", "parfait"}

def is_keyword(text):
    return (is_price(text) or is_number(text) or is_watch_brand(text)
            or is_cta(text) or is_question_word(text) or _norm(text) in SUPERLATIVES)

def mark(tokens):
    """Annote chaque token : t['kw'] = mot à forte valeur. Retourne tokens."""
    for t in tokens:
        t["kw"] = is_keyword(t["disp"])
    return tokens
```

- [ ] **Step 4: Lancer (succès)** — PASS.
- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/keywords.py backend/tests/test_keywords.py
git commit -m "feat(dyn): keywords module (single source of high-value words)"
```

---

## Task 2: Config (emphase + motion + transitions)

**Files:** Modify `backend/config.py`

- [ ] **Step 1: Ajouter à la fin de `backend/config.py`**
```python
EMPHASIS = dict(active_scale=130, kw_active_scale=152, kw_idle_scale=116,
                accent="&H0000FFFF&", kw_outline=6)
MOTION = dict(kenburns_zoom=1.10, punch_zoom=1.16, shake_px=10,
              zoom_period=2.5)
TRANSITIONS = dict(dur=0.12, default_type="fade")
```

- [ ] **Step 2: Commit**
```bash
git add backend/config.py
git commit -m "feat(dyn): emphasis/motion/transitions config"
```

---

## Task 3: Sous-titres « Premium Pop » (emphase mot par mot)

**Files:** Modify `backend/pipeline/subtitles.py`, Test `backend/tests/test_subtitles.py`

- [ ] **Step 1: Ajouter le test**
```python
# dans backend/tests/test_subtitles.py
def test_premium_emphasis(tmp_path):
    toks = [
        {"disp": "Cette", "sent": 0, "start": 0.0, "end": 0.3, "kw": False},
        {"disp": "Rolex", "sent": 0, "start": 0.3, "end": 0.8, "kw": True},
    ]
    out = str(tmp_path / "p.ass")
    build_ass(toks, 1, out, style="premium_pop")
    c = open(out, encoding="utf-8").read()
    assert "\\t(" in c            # animation pop
    assert "&H0000FFFF&" in c     # couleur accent (mot actif)
    assert "\\fscx152" in c or "\\fscy152" in c   # mot-clé plus gros
    assert "\\k" not in c and "\\fad" not in c    # pas de karaoké/fondu
```

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_subtitles.py::test_premium_emphasis -v` → FAIL.

- [ ] **Step 3: Ajouter le preset + le mode dans `subtitles.py`**

Dans le dict `STYLES`, ajouter :
```python
    "premium_pop": {"label": "Premium Pop (emphase mots-clés)", "font": "Arial Black", "size": 82,
        "primary": "&H00FFFFFF&", "secondary": "&H00FFFFFF&", "outline_col": "&H00000000&",
        "back_col": "&H00000000&", "border_style": 1, "outline": 5, "shadow": 2,
        "alignment": 5, "margin_v": 60, "mode": "premium"},
```
Après les imports de `subtitles.py`, ajouter :
```python
from backend.config import EMPHASIS
```
Dans `build_ass`, dans la boucle des chunks, ajouter une branche `premium` (avant le `else: # block`) :
```python
        elif st["mode"] == "premium":
            acc = EMPHASIS["accent"]
            for a in range(len(chunk)):
                wstart = chunk[a]["start"]
                wend = chunk[a + 1]["start"] if a + 1 < len(chunk) else chunk[a]["end"]
                if wend <= wstart:
                    wend = wstart + 0.08
                parts = []
                for j, wd in enumerate(chunk):
                    disp = wd["disp"].upper()
                    kw = wd.get("kw")
                    if j == a and kw:
                        s0 = EMPHASIS["kw_active_scale"]
                        tag = ("{\\fscx%d\\fscy%d\\t(0,90,\\fscx%d\\fscy%d)\\t(90,180,\\fscx100\\fscy100)"
                               "\\1c%s\\3c%s\\bord%d}") % (s0, s0, s0 + 8, s0 + 8, acc, acc, EMPHASIS["kw_outline"])
                        parts.append(tag + disp + "{\\r}")
                    elif j == a:
                        s0 = EMPHASIS["active_scale"]
                        parts.append("{\\fscx%d\\fscy%d\\t(0,120,\\fscx100\\fscy100)\\1c%s}%s{\\r}" % (s0, s0, acc, disp))
                    elif kw:
                        s0 = EMPHASIS["kw_idle_scale"]
                        parts.append("{\\fscx%d\\fscy%d\\1c%s}%s{\\r}" % (s0, s0, acc, disp))
                    else:
                        parts.append(disp)
                lines.append(f"Dialogue: 0,{ass_time(wstart)},{ass_time(wend)},Default,,0,0,0,, " + " ".join(parts))
```
Important : cette branche émet **une ligne par mot actif** (pas une seule par chunk) — elle remplace la création de ligne unique pour ce chunk. Veiller à ce que le `else: # block` et le `lines.append(... )` de fin de boucle ne s'exécutent **pas** pour le mode premium (la branche premier gère elle-même ses lignes ; utiliser `continue` après la branche premium si nécessaire selon la structure de la boucle).

- [ ] **Step 4: Lancer (succès)** — `pytest backend/tests/test_subtitles.py -v` → PASS (premium + non-régression des autres styles).

- [ ] **Step 5: Vérif visuelle** — rendre une frame sur fond noir avec `style="premium_pop"` sur des tokens dont un `kw=True`, vérifier : mot actif jaune agrandi, mot-clé plus gros. (`ffmpeg -f lavfi -i color=black:s=1080x1920 -vf ass=premium.ass -frames:v 1 out.png`)

- [ ] **Step 6: Commit**
```bash
git add backend/pipeline/subtitles.py backend/tests/test_subtitles.py
git commit -m "feat(dyn): premium subtitle emphasis (per-word pop + keyword emphasis)"
```

---

## Task 4: director.build_plan (timeline de décisions)

**Files:** Create `backend/pipeline/director.py`, Test `backend/tests/test_director.py`

- [ ] **Step 1: Test (échec)**
```python
# backend/tests/test_director.py
from backend.pipeline.director import build_plan

def test_plan_shape():
    tokens = [{"disp": "Rolex", "start": 1.0, "end": 1.4, "sent": 0, "kw": True},
              {"disp": "belle", "start": 1.4, "end": 1.8, "sent": 0, "kw": False}]
    ranges = [(0.0, 3.0), (3.0, 6.0)]
    plan = build_plan(tokens, 2, ranges, 6.0)
    assert any(m["kind"] == "kenburns" for m in plan["motion"])
    assert any(m["kind"] == "punch" and abs(m["start"] - 1.0) < 1e-6 for m in plan["motion"])
    # une transition à chaque cut sauf le premier
    assert len(plan["transitions"]) == 1 and abs(plan["transitions"][0]["at"] - 3.0) < 1e-6
```

- [ ] **Step 2: Lancer (échec)** — FAIL.

- [ ] **Step 3: Écrire `backend/pipeline/director.py`**
```python
from backend.config import TRANSITIONS

def build_plan(tokens, n_sent, ranges, duration):
    """Timeline de décisions visuelles (extensible). Aujourd'hui : Ken Burns par
    clip, punch sur mots-clés, transitions aux cuts."""
    motion = [{"kind": "kenburns", "start": s, "end": e} for (s, e) in ranges]
    for t in tokens:
        if t.get("kw"):
            motion.append({"kind": "punch", "start": t["start"]})
    transitions = [{"at": s, "type": TRANSITIONS["default_type"]} for (s, _e) in ranges[1:]]
    return {"motion": motion, "transitions": transitions}
```

- [ ] **Step 4: Lancer (succès)** — PASS.
- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/director.py backend/tests/test_director.py
git commit -m "feat(dyn): director embryo (motion + transitions timeline)"
```

---

## Task 5: SPIKE — méthode de zoom animé (risque n°1)

**But :** prouver une méthode de zoom **animé** qui **préserve le mouvement** de la vidéo, ou décider du repli. Investigation (pas de TDD).

- [ ] **Step 1: Rendre un clip avec `zoompan` et 2 frames du MÊME clip**
```bash
FF="C:/Users/User/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin"
CLIP="C:/Users/User/Downloads/Voix off/Clips/Muet/0604(1).mp4"
"$FF/ffmpeg.exe" -y -ss 1 -t 4 -i "$CLIP" -vf "scale=1404:2496:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0008,1.2)':d=1:s=1080x1920:fps=30,setsar=1" -an _zp.mp4 -loglevel error
"$FF/ffmpeg.exe" -y -ss 1.0 -i _zp.mp4 -frames:v 1 _z1.png -loglevel error
"$FF/ffmpeg.exe" -y -ss 1.4 -i _zp.mp4 -frames:v 1 _z2.png -loglevel error
"$FF/ffmpeg.exe" -i _z1.png -i _z2.png -lavfi psnr -f null - 2>&1 | grep -i "psnr"
```
Expected : si PSNR < ~35 dB entre 1.0 s et 1.4 s **dans le même clip**, le mouvement est préservé → `zoompan` est BON. Si PSNR très élevé (image quasi identique) → `zoompan` fige.

- [ ] **Step 2: Tester aussi `crop:eval=frame` (alternative)**
```bash
"$FF/ffmpeg.exe" -y -ss 1 -t 2 -i "$CLIP" -vf "scale=1404:2496:force_original_aspect_ratio=increase,crop=1080:1920,crop=w='iw/min(1+0.05*t,1.2)':h='ih/min(1+0.05*t,1.2)':eval=frame,scale=1080:1920" -an _crop.mp4 -loglevel error 2>&1 | tail -2
```
Expected : si la commande réussit → `crop:eval=frame` dispo (méthode de secours propre). Si "Option not found" → indisponible.

- [ ] **Step 3: Décision** — écrire dans `_SPIKE_MOTION.md` (à la racine) la méthode retenue : `zoompan` si mouvement préservé ; sinon `crop:eval=frame` ; sinon repli **zoom constant varié + punch par ré-échelonnage**. Nettoyer `_zp.mp4 _z*.png _crop.mp4`.

- [ ] **Step 4: Commit (note de décision)**
```bash
git add _SPIKE_MOTION.md
git commit -m "spike(dyn): chosen animated-zoom method documented"
```

---

## Task 6: Motion dans le rendu (Ken Burns + punch + shake)

**Files:** Modify `backend/pipeline/montage.py`, Test `backend/tests/test_montage.py`
**Pré-requis :** méthode de zoom retenue par la Task 5. Le code ci-dessous suppose **`zoompan` valide** (cas le plus probable). Si la Task 5 a conclu au repli, remplacer le filtre `zoompan` du `kenburns` par le zoom constant varié (même structure, sans la partie animée).

- [ ] **Step 1: Test (échec)**
```python
# dans backend/tests/test_montage.py
def test_render_with_plan(sample_audio, tmp_path):
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    plan = {"motion": [{"kind": "kenburns", "start": 0.0, "end": dur},
                       {"kind": "punch", "start": dur * 0.5}],
            "transitions": []}
    out = str(tmp_path / "plan.mp4")
    render(sample_audio, ass, [(0.0, dur)], out, plan=plan)
    assert os.path.exists(out)
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height", "-of", "csv=p=0", out])
    assert "1080,1920" in r.stdout
```

- [ ] **Step 2: Lancer (échec)** — `pytest backend/tests/test_montage.py::test_render_with_plan -v` → FAIL (signature `plan`).

- [ ] **Step 3: Modifier `render` dans `montage.py`** — ajouter `plan=None` à la signature ; dans la boucle vidéo par clip, si `plan`, appliquer un Ken Burns (zoompan) par clip et un shake sur les ranges qui contiennent un punch. Remplacer la construction du filtre vidéo par clip :
```python
    from backend.config import MOTION
    # index rapide : y a-t-il un punch dans [s,e] d'un clip ? (shake court)
    punches = [m["start"] for m in (plan or {}).get("motion", []) if m["kind"] == "punch"]
    fc = []
    tcum = 0.0
    for k in range(Ncl):
        zf = BOOST["punch_zoom"] if (boost and k == 0) else ZOOM
        cw, ch = int(W * zf), int(H * zf)
        chain = (f"[{k}:v]scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={W}:{H}")
        if plan:
            kb = MOTION["kenburns_zoom"]
            chain += (f",zoompan=z='min(zoom+0.0007,{kb})':d=1:"
                      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
            (s, e) = ranges[k]
            local_punch = [p - s for p in punches if s <= p < e]
            for pt in local_punch[:1]:
                spx = MOTION["shake_px"]
                chain += (f",crop=w={W}:h={H}:"
                          f"x='(in_w-{W})/2+{sx_expr(spx, pt)}':"
                          f"y='(in_h-{H})/2+{sy_expr(spx, pt)}'")
        chain += f",setsar=1,fps={FPS},format=yuv420p[v{k}]"
        fc.append(chain)
        tcum += (ranges[k][1] - ranges[k][0])
```
…où, en haut de `montage.py`, ajouter deux helpers d'expression de shake :
```python
def sx_expr(px, t0):
    return f"if(between(t,{t0:.2f},{t0+0.3:.2f}),{px}*sin((t-{t0:.2f})*60),0)"
def sy_expr(px, t0):
    return f"if(between(t,{t0:.2f},{t0+0.3:.2f}),{px}*sin((t-{t0:.2f})*47),0)"
```
(Le reste de `render` — concat, ass, audio — inchangé. `plan=None` ⇒ comportement actuel.)

- [ ] **Step 4: Lancer** — `pytest backend/tests/test_montage.py -k "plan or boost or render" -v` → PASS. Puis **vérif visuelle** : extraire 2 frames du même clip de la vidéo `plan.mp4` → le contenu doit bouger (Ken Burns) ; autour du punch, léger shake.

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/montage.py backend/tests/test_montage.py
git commit -m "feat(dyn): motion in render (ken burns + shake on punches)"
```

---

## Task 7: Transitions length-preserving

**Files:** Modify `backend/pipeline/montage.py`, Test `backend/tests/test_montage.py`

- [ ] **Step 1: Test (échec)**
```python
def test_render_transitions(sample_audio, tmp_path):
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    plan = {"motion": [], "transitions": [{"at": dur * 0.5, "type": "fade"}]}
    out = str(tmp_path / "tr.mp4")
    render(sample_audio, ass, [(0.0, dur * 0.5), (dur * 0.5, dur)], out, plan=plan)
    assert os.path.exists(out)
```

- [ ] **Step 2: Lancer (échec)** — FAIL.

- [ ] **Step 3: Ajouter le fade d'entrée par clip (sauf le 1er)** — dans la boucle vidéo de `render`, après `crop={W}:{H}` (et avant `setsar`), si `plan` et `k>0`, ajouter un court fondu d'entrée (longueur = `TRANSITIONS["dur"]`, sur la **timeline locale du clip**, donc 0 → dur) :
```python
        if plan and k > 0:
            from backend.config import TRANSITIONS
            chain += f",fade=t=in:st=0:d={TRANSITIONS['dur']:.3f}"
```
(Le fondu est interne au clip → **ne change pas la durée totale** → voix toujours synchro.)

- [ ] **Step 4: Lancer** — `pytest backend/tests/test_montage.py -k "transitions or plan or render" -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/pipeline/montage.py backend/tests/test_montage.py
git commit -m "feat(dyn): length-preserving fade transitions at cuts"
```

---

## Task 8: Câblage service (keywords + director + premium)

**Files:** Modify `backend/service.py`, Test `backend/tests/test_server.py`

- [ ] **Step 1: Modifier `make_video` dans `service.py`** — importer et utiliser keywords + director :

En haut, ajouter :
```python
from backend.pipeline import keywords, director
```
Remplacer le corps de `make_video` par :
```python
def make_video(clean_path, text, out_path, style="karaoke_yellow", boost=False):
    words, duration = T.transcribe(clean_path)
    tokens, n_sent = align.tokenize(text)
    align.align(tokens, words)
    keywords.mark(tokens)
    job = os.path.dirname(clean_path)
    ass = os.path.join(job, "subs.ass")
    subtitles.build_ass(tokens, n_sent, ass, style=style)
    ranges = montage.sentence_ranges(tokens, n_sent, duration)
    if boost:
        ranges = montage.apply_boost_cuts(ranges, BOOST["hook_dur"], BOOST["hook_cut"])
    plan = director.build_plan(tokens, n_sent, ranges, duration)
    sfx_events = None
    if boost:
        sw = [T.Word(t["disp"], t["start"], t["end"], 1.0) for t in tokens]
        phrases = []
        for si in range(n_sent):
            ts = [t for t in tokens if t["sent"] == si]
            if ts:
                phrases.append((ts[0]["start"], ts[-1]["end"]))
        cuts = [r[0] for r in ranges if r[0] > 0.01]
        sfx_events = sfx_plan.generate_sfx(sw, phrases, cuts, duration, BOOST["hook_dur"])
    montage.render(clean_path, ass, ranges, out_path, boost=boost,
                   sfx_events=sfx_events, plan=plan)
    return out_path
```

- [ ] **Step 2: Test serveur (preview avec style premium)** — ajouter dans `backend/tests/test_server.py` :
```python
def test_preview_premium_style(sample_audio, tmp_path):
    data = client.post("/load", json={"audio_path": sample_audio}).json()
    out = str(tmp_path / "prem.mp4")
    r = client.post("/preview", json={"clean_path": data["clean_path"], "text": data["transcript"],
                                      "out_path": out, "style": "premium_pop"})
    import os
    assert os.path.exists(r.json()["video_path"])
```

- [ ] **Step 3: Lancer** — `pytest backend/tests/test_server.py::test_preview_premium_style -v` → PASS.

- [ ] **Step 4: Commit**
```bash
git add backend/service.py backend/tests/test_server.py
git commit -m "feat(dyn): wire keywords+director+premium into make_video"
```

---

## Task 9: Vérification finale

- [ ] **Step 1: Suite complète** — `pytest backend/tests/ -q` → tous PASS (non-régression incluse).
- [ ] **Step 2: Test manuel** — `npm start` : déposer un audio, choisir style **Premium Pop**, Générer. Vérifier : mots qui poppent (mot-clé plus gros/jaune), image qui bouge (Ken Burns) + shake léger sur mots-clés, petit fondu aux changements de plan, **voix toujours synchro**.
- [ ] **Step 3: Nettoyer** le fichier `_SPIKE_MOTION.md` si tu ne veux pas le garder (optionnel).

---

## Self-Review
- **Couverture spec :** keywords (T1) · emphase premium (T3) · director timeline (T4) · spike motion (T5) · motion render ken burns+punch+shake (T6) · transitions length-preserving (T7) · câblage make_video (T8) · config (T2) · non-régression (tests conservés, `plan=None` rétro-compatible). ✓
- **Types :** `keywords.mark(tokens)->tokens (t['kw'])` ; `director.build_plan(tokens,n_sent,ranges,duration)->{motion,transitions}` ; `montage.render(..., plan=None)` ; `subtitles.build_ass(..., style='premium_pop')`. Cohérent. ✓
- **Risque connu :** Task 6 dépend du résultat du spike (Task 5) — le code suppose `zoompan` valide, repli documenté. ✓
- **Pas de placeholder.** ✓
