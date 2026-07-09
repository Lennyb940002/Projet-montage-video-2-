# -*- coding: utf-8 -*-
"""Génère N vidéos 'rafale' à partir des PHOTOS PRODUIT FOND BLANC.
Intro hook beat-syncé (calé sur le drop) + montres fond blanc : nom (noir) puis
PRIX (rouge) qui apparaît juste avant la montre suivante. 1 son différent par vidéo.

python deploy/make_wb_videos.py
"""
import os, sys, json, glob, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E
from deploy import rafale_registry as REG

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
BANK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "backend", "silent", "banks", "intro_streetwear")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"

TARGET_DUR = 15.0
DROP_NUDGE = 0.0        # drop ET image au MÊME instant (sur l'impact détecté)
PRICE = "194,90 €"
# hook / son / photo d'intro : piochés dans le registre anti-répétition (jamais les mêmes)

# (sous-chaîne dossier, nom affiché, indices d'images à écarter)
MODELS = [("Datejust", "Datejust", ()),
          ("Daytona", "Daytona", ()),
          ("Santos", "Santos", (0,)),          # écarte la Santos "FUCK 9-5" (index 0)
          ("Royal Oak", "Royal Oak", ())]


def imgs_for(sub, skip):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    ims = sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))
    return [f for i, f in enumerate(ims) if i not in skip]


IMG = {name: imgs_for(sub, skip) for (sub, name, skip) in MODELS}


def _build(vi, hook_id, key, intro_file):
    a = ANALYSIS[key]; beats = a["beats"]; b0 = beats[0]
    music = os.path.join(ASSETS, "music", f"{key}.wav")

    hook0 = [{"text": t, "color": c, "size": (44 if t.startswith("part") else 150)}
             for (t, c) in REG.HOOKS[hook_id]]
    hook, intro_dur = E.plan_intro(hook0, beats, a.get("drop"))
    intro_dur = round(intro_dur + DROP_NUDGE, 3)

    # rafale : 4 montres, coupes sur beats
    g = [round(b - b0, 3) for b in beats]
    order = MODELS[vi % 4:] + MODELS[:vi % 4]
    n = len(order)
    span = TARGET_DUR - intro_dur
    bounds = [intro_dur]
    for j in range(1, n):
        tgt = intro_dur + span * j / n
        cand = min((x for x in g if x > bounds[-1] + 1.0), key=lambda x: abs(x - tgt), default=tgt)
        bounds.append(round(cand, 3))
    bounds.append(round(TARGET_DUR, 3))

    wd = tempfile.mkdtemp(prefix="wb_")
    intro = os.path.join(wd, "intro.mp4")
    E.render_intro(os.path.join(BANK, intro_file), hook, intro, intro_dur, wd)
    parts = [intro]
    for k, (sub, name, _) in enumerate(order):
        ims = IMG[name]
        img = ims[vi % len(ims)]
        seg = round(max(1.8, bounds[k + 1] - bounds[k]), 3)
        o = os.path.join(wd, f"seg_{k+1}.mp4")
        E.render_photo(img, seg, name, PRICE, o, wd, k + 1, price_lead=0.7)
        parts.append(o)

    visual = os.path.join(wd, "visual.mp4")
    E.concat(parts, visual, wd)
    vdur = E.probe_dur(visual)
    out = os.path.join(OUT_DIR, f"rafale_wb_{vi+1}.mp4")
    E.add_music(visual, music, 0.0, vdur, out)
    print(f"VIDEO {vi+1}: {os.path.basename(out)}  dur={vdur:.1f}s  hook={hook_id}  "
          f"son={a['name']}  intro={intro_file}  montres={[m[1] for m in order]}")
    return out


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    u = REG.load()
    for vi in range(N):
        hk, sd, it = REG.pick(u)          # jamais le même hook / son / intro
        _build(vi, hk, sd, it)
    REG.save(u)
    print(f"registre mis à jour ({len(u['used'])} combinaisons utilisées au total)")
