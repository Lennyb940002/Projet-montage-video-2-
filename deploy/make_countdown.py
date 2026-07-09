# -*- coding: utf-8 -*-
"""Concept COUNTDOWN : Top 3 en suspense (#3 -> #2 -> #1) sur les beats. Fond blanc."""
import os, sys, glob, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"
MUSIC = "11"; TITLE1 = "TOP 3"; TITLE2 = "qui font le plus riche"
# du #3 (montré en 1er) au #1
RANKED = [("#3", "Datejust", 0, "Datejust"), ("#2", "Santos", 1, "Santos"),
          ("#1", "Royal Oak", 0, "Royal Oak")]
OUT_NAME = "countdown_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def render_title(dur, out, wd):
    p1 = os.path.join(wd, "t1.txt"); open(p1, "w", encoding="utf-8").write(TITLE1)
    p2 = os.path.join(wd, "t2.txt"); open(p2, "w", encoding="utf-8").write(TITLE2)
    dt = [E._drawtext(p1, int(E.H * 0.40), 220, E.INK, 0.05, 6, "white@0.5"),
          E._drawtext(p2, int(E.H * 0.56), 66, E.RED, 0.20, 5, "white@0.6")]
    vf = "color=white:s=1080x1920,setsar=1," + ",".join(dt) + ",format=yuv420p"
    frames = int(round(dur * E.FPS))
    E.run([E.FF, "-y", "-f", "lavfi", "-i", f"color=white:s=1080x1920:d={dur}",
           "-vf", ",".join(dt) + ",format=yuv420p", "-frames:v", str(frames), *E._X264, "-an", out])


def render_ranked(img, seg, rank, name, out, wd, idx):
    pr = os.path.join(wd, f"r{idx}.txt"); open(pr, "w", encoding="utf-8").write(rank)
    pn = os.path.join(wd, f"n{idx}.txt"); open(pn, "w", encoding="utf-8").write(name)
    dt = [E._drawtext(pr, int(E.H * 0.05), 150, E.RED, 0.10, 8, "white@0.85"),
          E._drawtext(pn, int(E.H * 0.86), 70, E.INK, 0.22, 5, "white@0.85")]
    vf = ("scale=980:1400:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:(ow-iw)/2:300:color=white,setsar=1,"
          + ",".join(dt) + ",format=yuv420p")
    frames = int(round(seg * E.FPS))
    E.run([E.FF, "-y", "-loop", "1", "-t", f"{seg}", "-i", img, "-vf", vf,
           "-frames:v", str(frames), *E._X264, "-an", out])


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    bt = [round(b - b0, 3) for b in beats]
    wd = tempfile.mkdtemp(prefix="cd_")
    title = os.path.join(wd, "title.mp4")
    t_dur = round(bt[min(4, len(bt) - 1)], 3)              # titre jusqu'au 4e beat
    render_title(t_dur, title, wd)
    parts = [title]
    show_beats = [bt[min(4 + 3 * k, len(bt) - 1)] for k in range(len(RANKED))] + [bt[min(4 + 3 * len(RANKED), len(bt) - 1)] + 2.2]
    for k, (rank, sub, idx, name) in enumerate(RANKED):
        seg = round(show_beats[k + 1] - show_beats[k], 3) if k + 1 < len(show_beats) else 2.5
        o = os.path.join(wd, f"seg{k}.mp4")
        render_ranked(_wb(sub, idx), max(1.8, seg), rank, name, o, wd, k)
        parts.append(o)
    visual = os.path.join(wd, "visual.mp4"); E.concat(parts, visual, wd)
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(visual, music, 0.0, E.probe_dur(visual), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s")


if __name__ == "__main__":
    main()
