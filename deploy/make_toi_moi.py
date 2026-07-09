# -*- coding: utf-8 -*-
"""Concept TOI vs MOI : l'objection 'c'est du fake' démontée en meme, les specs
qui tombent sur les beats. Fond blanc (montre), texte foncé."""
import os, sys, glob, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"
GREEN = "#0FA958"
WATCH = ("Royal Oak", 0)
MUSIC = "07"
TOI = "TOI : « c'est du fake »"
SPECS = ["+ Saphir anti-rayures", "+ Mouvement NH35 auto", "+ Acier 316L"]
OUT_NAME = "toimoi_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    bt = [round(b - b0, 3) for b in beats]
    # "MOI :" + 3 specs sur des beats
    spec_beats = [bt[min(3 + 2 * k, len(bt) - 1)] for k in range(len(SPECS))]
    dur = round(spec_beats[-1] + 2.2, 3)
    wd = tempfile.mkdtemp(prefix="tm_")
    ft = os.path.join(wd, "toi.txt"); open(ft, "w", encoding="utf-8").write(TOI)
    fm = os.path.join(wd, "moi.txt"); open(fm, "w", encoding="utf-8").write("MOI :")
    dt = [E._drawtext(ft, int(E.H * 0.05), 60, E.RED, 0.1, 5, "white@0.9"),
          E._drawtext(fm, int(E.H * 0.60), 66, E.INK, bt[2], 5, "white@0.85")]
    y = int(E.H * 0.67)
    for k, s in enumerate(SPECS):
        p = os.path.join(wd, f"s{k}.txt"); open(p, "w", encoding="utf-8").write(s)
        dt.append(E._drawtext(p, y, 58, GREEN, spec_beats[k], 4, "white@0.85"))
        y += 92
    vf = ("scale=980:1400:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:(ow-iw)/2:120:color=white,setsar=1,"
          + ",".join(dt) + ",format=yuv420p")
    frames = int(round(dur * E.FPS)); seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", "-loop", "1", "-t", f"{dur}", "-i", _wb(*WATCH),
           "-vf", vf, "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  specs@{spec_beats}")


if __name__ == "__main__":
    main()
