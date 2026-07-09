# -*- coding: utf-8 -*-
"""Concept POV / storytime relatable : texte meme sur un plan poignet, punchline
sur le drop. Faceless, zéro tournage."""
import os, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))

CLIP = r"C:\Users\zbull\Downloads\Daytona Blue Saphire.mp4"
CROP_WM = 120
MUSIC = "07"
SETUP = [("POV :", "white"), ("tu dis à tout", "white"), ("le monde que", "white"), ("c'est une vraie", "yellow")]
PUNCH = "elle est à 195€"
OUT_NAME = "pov_test.mp4"


def render_seg(clip, start, dur, chunks, punch, punch_at, out, wd):
    files = E._write_textfiles(chunks, wd)
    sizes = [E._fit_size(c["text"], 120) for c in chunks]
    heights = [int(s * 1.15) for s in sizes]
    y = int(E.H * 0.09)
    dt = []
    for i, ch in enumerate(chunks):
        color = E.YELLOW if ch["color"] == "yellow" else E.WHITE
        dt.append(E._drawtext(files[i], y, sizes[i], color, ch["appear"], max(6, int(sizes[i]*0.06))))
        y += heights[i]
    if punch:
        pf = os.path.join(wd, "punch.txt"); open(pf, "w", encoding="utf-8").write(punch)
        dt.append(E._drawtext(pf, int(E.H*0.80), 96, E.RED, punch_at, borderw=10, border_color="white@0.9"))
    avail = E.probe_dur(clip) - start
    factor = max(1.0, dur/max(0.1, avail))
    vf = (f"crop=iw:ih-{CROP_WM}:0:0,setpts={factor:.4f}*PTS,"
          "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
          + ",".join(dt) + ",format=yuv420p")
    frames = int(round(dur*E.FPS))
    E.run([E.FF, "-y", "-ss", f"{start}", "-i", clip, "-vf", vf, "-frames:v", str(frames), *E._X264, "-an", out])


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    clip_dur = E.probe_dur(CLIP)
    total = round(clip_dur - 0.2, 3)
    # punchline calée sur un beat, mais DANS la durée du clip (laisse ~1.5s de hold)
    bt = [round(b - b0, 3) for b in beats]
    target = min((a.get("drop") or 3.2), total - 1.5)
    punch_at = min([x for x in bt if x <= total - 1.2] or [target], key=lambda x: abs(x - target))
    chunks = [{"text": t, "color": c, "size": 120} for (t, c) in SETUP]
    chunks, _ = E.plan_intro(chunks, beats, punch_at)             # setup monte avant la punch
    wd = tempfile.mkdtemp(prefix="pov_")
    seg = os.path.join(wd, "seg.mp4")
    render_seg(CLIP, 0.2, total, chunks, PUNCH, round(punch_at, 3), seg, wd)
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  punch@{punch_at:.1f}s")


if __name__ == "__main__":
    main()
