# -*- coding: utf-8 -*-
"""Concept STYLING '1 tenue = 1 montre' : photo streetwear (intro) + texte, et
SUR LE DROP la montre qui matche surgit en carte fond blanc + son nom."""
import os, sys, glob, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
BANK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "backend", "silent", "banks", "intro_streetwear")
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"

INTRO = "intro_20.jpg"
WATCH_FOLDER = "Royal Oak"; WATCH_IDX = 0; WATCH_NAME = "Royal Oak Or Rose · 195€"
MUSIC = "39"
HOOK = [("La montre", "white"), ("qui finit", "white"), ("CE fit", "yellow")]
OUT_NAME = "styling_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def make_card(img, out):
    # montre contenue sur carte blanche 620x760 (bordure douce)
    E.run([E.FF, "-y", "-f", "lavfi", "-i", "color=white:s=620x760", "-i", img,
           "-filter_complex", "[1]scale=560:700:force_original_aspect_ratio=decrease[w];"
           "[0][w]overlay=(W-w)/2:(H-h)/2,drawbox=x=0:y=0:w=620:h=760:color=black@0.15:t=4",
           "-frames:v", "1", out])


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    chunks = [{"text": t, "color": c, "size": 120} for (t, c) in HOOK]
    chunks, drop = E.plan_intro(chunks, beats, a.get("drop"))
    dur = round(drop + 3.5, 3)
    wd = tempfile.mkdtemp(prefix="styl_")
    card = os.path.join(wd, "card.png"); make_card(_wb(WATCH_FOLDER, WATCH_IDX), card)
    nf = os.path.join(wd, "name.txt"); open(nf, "w", encoding="utf-8").write(WATCH_NAME)

    files = E._write_textfiles(chunks, wd)
    sizes = [E._fit_size(c["text"], 120) for c in chunks]
    heights = [int(s*1.15) for s in sizes]; y = int(E.H*0.08)
    dt = []
    for i, ch in enumerate(chunks):
        color = E.YELLOW if ch["color"] == "yellow" else E.WHITE
        dt.append(E._drawtext(files[i], y, sizes[i], color, ch["appear"], max(6, int(sizes[i]*0.06))))
        y += heights[i]
    name_dt = E._drawtext(nf, int(E.H*0.90), 58, E.WHITE, round(drop+0.15, 3), borderw=7)
    frames = int(round(dur*E.FPS))
    # photo streetwear (fixe) ; carte montre en overlay qui surgit sur le drop
    fc = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg];"
          f"[bg][1:v]overlay=(W-w)/2:1050:enable='gte(t,{drop})'[o];"
          "[o]" + ",".join(dt) + "," + name_dt + ",format=yuv420p")
    seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", "-loop", "1", "-t", f"{dur}", "-i", os.path.join(BANK, INTRO),
           "-loop", "1", "-t", f"{dur}", "-i", card, "-filter_complex", fc,
           "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  montre surgit @{drop:.1f}s")


if __name__ == "__main__":
    main()
