# -*- coding: utf-8 -*-
"""Concept #8 REPONSE A UN COMMENTAIRE (preuve sociale) : bulle commentaire style
Insta 'c'est où ??' sur un plan poignet, 'je t'ai envoyé en DM', CTA 'commente OU'."""
import os, sys, tempfile, json
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E
from deploy.make_dm import build_pill

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
FONT = r"C:\Windows\Fonts\ariblk.ttf"
FONTR = r"C:\Windows\Fonts\arial.ttf"
CLIP = r"C:\Users\zbull\Downloads\Royal Oak Or rose.mp4"
CROP_WM = 120
MUSIC = "39"
USER = "camille_ptx"; COMMENT = "c'est où ?? 🔥 j'la veux"
REPLY = [("Je t'ai envoyé", "white"), ("le lien en DM", "yellow")]
CTA = "Commente OÙ"
OUT_NAME = "commentreply_test.mp4"


def build_comment(out):
    W_, H_ = 960, 190
    img = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W_ - 1, H_ - 1], radius=40, fill=(255, 255, 255, 245))
    d.ellipse([28, 40, 138, 150], fill=(200, 170, 120))
    d.text((83, 95), USER[0].upper(), font=ImageFont.truetype(FONT, 56), fill=(255, 255, 255), anchor="mm")
    d.text((165, 52), USER, font=ImageFont.truetype(FONT, 40), fill=(20, 20, 20))
    try:
        fr = ImageFont.truetype(FONTR, 44)
    except Exception:
        fr = ImageFont.truetype(FONT, 40)
    d.text((165, 108), COMMENT, font=fr, fill=(60, 60, 60))
    d.text((W_ - 70, 95), "♥", font=ImageFont.truetype(FONTR, 46), fill=(230, 30, 60), anchor="mm")
    img.save(out)
    return W_, H_


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    clip_dur = E.probe_dur(CLIP); total = round(clip_dur - 0.2, 3)
    b0 = beats[0]; bt = [round(b - b0, 3) for b in beats]
    target = min((a.get("drop") or 3.2), total - 1.4)
    drop = min([x for x in bt if x <= total - 1.1] or [target], key=lambda x: abs(x - target))
    chunks = [{"text": t, "color": c, "size": 110} for (t, c) in REPLY]
    chunks, _ = E.plan_intro(chunks, beats, drop)
    wd = tempfile.mkdtemp(prefix="cr_")
    com = os.path.join(wd, "com.png"); cw, ch = build_comment(com)
    pill = os.path.join(wd, "pill.png"); pw, ph = build_pill(CTA, pill, (37, 211, 102))

    files = E._write_textfiles(chunks, wd)
    sizes = [E._fit_size(c["text"], 110) for c in chunks]
    heights = [int(s * 1.14) for s in sizes]; y = int(E.H * 0.42); dt = []
    for i, ch in enumerate(chunks):
        color = E.YELLOW if ch["color"] == "yellow" else E.WHITE
        dt.append(E._drawtext(files[i], y, sizes[i], color, ch["appear"], max(6, int(sizes[i] * 0.06))))
        y += heights[i]
    factor = max(1.0, total / max(0.1, clip_dur - 0.2))
    px, py = (E.W - pw) // 2, int(E.H * 0.80) - ph // 2
    fc = (f"[0:v]crop=iw:ih-{CROP_WM}:0:0,setpts={factor:.4f}*PTS,"
          "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
          + ",".join(dt) + f"[v];"
          f"[v][1:v]overlay=(W-w)/2:150[v2];"
          f"[v2][2:v]overlay={px}:{py}:enable='{E._esc(f'gte(t,{round(drop,3)})')}',format=yuv420p")
    frames = int(round(total * E.FPS)); seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", "-ss", "0.2", "-i", CLIP, "-loop", "1", "-t", f"{total}", "-i", com,
           "-loop", "1", "-t", f"{total}", "-i", pill, "-filter_complex", fc,
           "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  CTA@{drop:.1f}s")


if __name__ == "__main__":
    main()
