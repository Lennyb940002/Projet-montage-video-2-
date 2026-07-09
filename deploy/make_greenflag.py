# -*- coding: utf-8 -*-
"""Concept GREEN FLAG : plan poignet + punchline dating/personnalité sur le drop."""
import os, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
GREEN = "#25D366"
CLIP = r"C:\Users\zbull\Downloads\Royal Oak Or rose.mp4"
CROP_WM = 120
MUSIC = "39"
SETUP = [("GREEN FLAG", "green"), ("il porte une", "white"), ("montre à 195€", "white")]
PUNCH = "pas 40 000€ de dette"
OUT_NAME = "greenflag_test.mp4"


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    clip_dur = E.probe_dur(CLIP); total = round(clip_dur - 0.2, 3)
    bt = [round(b - b0, 3) for b in beats]
    target = min((a.get("drop") or 3.2), total - 1.4)
    punch_at = min([x for x in bt if x <= total - 1.1] or [target], key=lambda x: abs(x - target))
    chunks = [{"text": t, "color": c, "size": 120} for (t, c) in SETUP]
    chunks, _ = E.plan_intro(chunks, beats, punch_at)
    wd = tempfile.mkdtemp(prefix="gf_")
    files = E._write_textfiles(chunks, wd)
    sizes = [E._fit_size(c["text"], 120) for c in chunks]
    heights = [int(s * 1.15) for s in sizes]; y = int(E.H * 0.09); dt = []
    for i, ch in enumerate(chunks):
        color = GREEN if ch["color"] == "green" else E.WHITE
        dt.append(E._drawtext(files[i], y, sizes[i], color, ch["appear"], max(6, int(sizes[i] * 0.06))))
        y += heights[i]
    pf = os.path.join(wd, "p.txt"); open(pf, "w", encoding="utf-8").write(PUNCH)
    dt.append(E._drawtext(pf, int(E.H * 0.80), 92, GREEN, round(punch_at, 3), borderw=10, border_color="black@0.9"))
    factor = max(1.0, total / max(0.1, clip_dur - 0.2))
    vf = (f"crop=iw:ih-{CROP_WM}:0:0,setpts={factor:.4f}*PTS,"
          "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
          + ",".join(dt) + ",format=yuv420p")
    frames = int(round(total * E.FPS)); seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", "-ss", "0.2", "-i", CLIP, "-vf", vf, "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  punch@{punch_at:.1f}s")


if __name__ == "__main__":
    main()
