# -*- coding: utf-8 -*-
"""Concept 'CE QUE TU PAIES VRAIMENT' : décompose le prix du luxe, la punchline
195€ tombe sur le drop. Fond blanc, éducatif / anti-snob."""
import os, sys, glob, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"
GREEN = "#0FA958"
WATCH = ("Daytona", 0)
MUSIC = "39"
TOP = "Une Rolex à 40 000€ :"
LINES = [("• 2% de matière", "ink"), ("• 98% le nom", "red"), ("Nous : 100% produit", "green")]
PRICE = "195€"
OUT_NAME = "breakdown_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    bt = [round(b - b0, 3) for b in beats]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    line_beats = [bt[min(2 + 2 * k, len(bt) - 1)] for k in range(len(LINES))]
    drop = a.get("drop") or bt[min(9, len(bt) - 1)]
    drop = max(drop, line_beats[-1] + 0.8)
    dur = round(drop + 3.0, 3)
    wd = tempfile.mkdtemp(prefix="bd_")
    ft = os.path.join(wd, "top.txt"); open(ft, "w", encoding="utf-8").write(TOP)
    dt = [E._drawtext(ft, int(E.H * 0.05), 62, E.INK, 0.1, 5, "white@0.9")]
    y = int(E.H * 0.63)
    for k, (txt, col) in enumerate(LINES):
        p = os.path.join(wd, f"l{k}.txt"); open(p, "w", encoding="utf-8").write(txt)
        color = {"red": E.RED, "green": GREEN}.get(col, E.INK)
        dt.append(E._drawtext(p, y, 58, color, line_beats[k], 4, "white@0.85")); y += 92
    pf = os.path.join(wd, "price.txt"); open(pf, "w", encoding="utf-8").write(PRICE)
    dt.append(E._drawtext(pf, int(E.H * 0.85), 150, E.RED, round(drop, 3), 10, "white@0.9"))
    vf = ("scale=980:1350:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:(ow-iw)/2:120:color=white,setsar=1,"
          + ",".join(dt) + ",format=yuv420p")
    frames = int(round(dur * E.FPS)); seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", "-loop", "1", "-t", f"{dur}", "-i", _wb(*WATCH),
           "-vf", vf, "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  195€@{drop:.1f}s")


if __name__ == "__main__":
    main()
