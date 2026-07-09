# -*- coding: utf-8 -*-
"""Concept 'CE QUE TA MONTRE DIT DE TOI' : intro hook + chaque montre fond blanc
avec une punchline personnalité (tag-a-friend)."""
import os, sys, glob, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
BANK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "backend", "silent", "banks", "intro_streetwear")
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"
MUSIC = "05"; INTRO = "intro_07.jpg"; TARGET = 15.0
HOOK = [("Ce que ta", "white"), ("montre", "white"), ("dit de toi", "yellow"), ("part 1", "white")]
TRAITS = [("Royal Oak", 0, "tu veux qu'on te remarque"),
          ("Daytona", 0, "tu vas vite en tout"),
          ("Datejust", 0, "tu joues la sécurité"),
          ("Santos", 1, "tu sors du moule")]
OUT_NAME = "personality_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    hook = [{"text": t, "color": c, "size": (44 if t.startswith("part") else 150)} for (t, c) in HOOK]
    hook, intro_dur = E.plan_intro(hook, beats, a.get("drop"))
    g = [round(b - b0, 3) for b in beats]; n = len(TRAITS)
    span = TARGET - intro_dur; bounds = [intro_dur]
    for j in range(1, n):
        tgt = intro_dur + span * j / n
        bounds.append(round(min((x for x in g if x > bounds[-1] + 1.0), key=lambda x: abs(x - tgt), default=tgt), 3))
    bounds.append(round(TARGET, 3))
    wd = tempfile.mkdtemp(prefix="perso_")
    intro = os.path.join(wd, "intro.mp4")
    E.render_intro(os.path.join(BANK, INTRO), hook, intro, intro_dur, wd)
    parts = [intro]
    for k, (sub, idx, trait) in enumerate(TRAITS):
        seg = round(max(1.8, bounds[k + 1] - bounds[k]), 3)
        o = os.path.join(wd, f"s{k}.mp4")
        E.render_photo(_wb(sub, idx), seg, trait, "", o, wd, k + 1, price_lead=0.6)
        parts.append(o)
    visual = os.path.join(wd, "visual.mp4"); E.concat(parts, visual, wd)
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(visual, music, 0.0, E.probe_dur(visual), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s")


if __name__ == "__main__":
    main()
