# -*- coding: utf-8 -*-
"""Concept DEVINE LE PRIX (face-à-face) : 2 montres empilées, question qui monte,
puis SUR LE DROP la révélation (les deux à 195€). Interaction / comment-bait."""
import os, sys, glob, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"

TOP = ("Daytona", 0); BOTTOM = ("Datejust", 0)
MUSIC = "11"
QUESTION = [("Une à 40 000€", "white"), ("une à 195€", "white"), ("laquelle ?", "yellow")]
REVEAL = "LES 2 = 195€"
OUT_NAME = "devine_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def composite(a_img, b_img, out):
    fc = ("[1]scale=760:-1:force_original_aspect_ratio=decrease[a];"
          "[2]scale=760:-1:force_original_aspect_ratio=decrease[b];"
          "[0][a]overlay=(W-w)/2:180[t];[t][b]overlay=(W-w)/2:1080,"
          "drawbox=x=90:y=958:w=900:h=4:color=black@0.15:t=fill")
    E.run([E.FF, "-y", "-f", "lavfi", "-i", "color=white:s=1080x1920",
           "-i", a_img, "-i", b_img, "-filter_complex", fc, "-frames:v", "1", out])


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    chunks = [{"text": t, "color": c, "size": 96} for (t, c) in QUESTION]
    chunks, drop = E.plan_intro(chunks, beats, a.get("drop"))
    dur = round(drop + 3.2, 3)
    wd = tempfile.mkdtemp(prefix="dev_")
    comp = os.path.join(wd, "comp.png"); composite(_wb(*TOP), _wb(*BOTTOM), comp)

    # labels A / B (toujours visibles)
    la = os.path.join(wd, "A.txt"); open(la, "w", encoding="utf-8").write("A")
    lb = os.path.join(wd, "B.txt"); open(lb, "w", encoding="utf-8").write("B")
    rf = os.path.join(wd, "rev.txt"); open(rf, "w", encoding="utf-8").write(REVEAL)
    files = E._write_textfiles(chunks, wd)
    dt = [E._drawtext(la, 300, 84, E.INK, 0.0, 4, "white@0.8").replace("x=(w-text_w)/2", "x=110"),
          E._drawtext(lb, 1200, 84, E.INK, 0.0, 4, "white@0.8").replace("x=(w-text_w)/2", "x=110")]
    # question empilée en haut
    y = 20
    for i, ch in enumerate(chunks):
        s = E._fit_size(ch["text"], 84)
        color = E.YELLOW if ch["color"] == "yellow" else E.INK
        dt.append(E._drawtext(files[i], y, s, color, ch["appear"], 4, "white@0.85"))
        y += int(s*1.1)
    # révélation au milieu, sur le drop
    dt.append(E._drawtext(rf, 905, 130, E.RED, round(drop, 3), 10, "white@0.95"))
    vf = ("scale=1080:1920,setsar=1," + ",".join(dt) + ",format=yuv420p")
    frames = int(round(dur*E.FPS))
    seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", "-loop", "1", "-t", f"{dur}", "-i", comp, "-vf", vf,
           "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  reveal@{drop:.1f}s")


if __name__ == "__main__":
    main()
