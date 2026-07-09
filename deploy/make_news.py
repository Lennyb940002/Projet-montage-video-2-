# -*- coding: utf-8 -*-
"""Concept FAUX BANDEAU PRESSE : chyron 'BREAKING' + titre choc sur la montre,
punch 195€ sur le drop. Format news = crédibilité + curiosité."""
import os, sys, glob, tempfile, json
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"
FONT = r"C:\Windows\Fonts\ariblk.ttf"
FONTR = r"C:\Windows\Fonts\arial.ttf"
W, H = 1080, 1920
WATCH = ("Daytona", 0)
MUSIC = "01"
TAG = "BREAKING"
HEADLINE = "Une montre à 195€ fait paniquer Rolex"
PRICE = "195€"
OUT_NAME = "news_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def _wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textbbox((0, 0), t, font=font)[2] <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def build_live(out):
    img = Image.new("RGBA", (330, 74), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, 330, 74], 12, fill=(20, 20, 24, 235))
    d.ellipse([22, 26, 52, 56], fill=(230, 30, 50))
    d.text((70, 37), "EN DIRECT", font=ImageFont.truetype(FONT, 34), fill=(255, 255, 255), anchor="lm")
    img.save(out); return img.size


def build_chyron(out):
    Hc = 250
    img = Image.new("RGBA", (W, Hc), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle([40, 30, 360, 150], fill=(200, 20, 40))                 # bloc rouge BREAKING
    d.text((200, 90), TAG, font=ImageFont.truetype(FONT, 56), fill=(255, 255, 255), anchor="mm")
    d.rectangle([360, 30, 1040, 150], fill=(255, 255, 255))             # bloc blanc titre
    fr = ImageFont.truetype(FONT, 40)
    lines = _wrap(d, HEADLINE, fr, 650)[:2]
    y = 90 - (len(lines) - 1) * 24
    for ln in lines:
        d.text((385, y), ln, font=fr, fill=(15, 15, 20), anchor="lm"); y += 48
    d.rectangle([40, 150, 1040, 165], fill=(200, 20, 40))               # liseré rouge bas
    img.save(out); return img.size


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    bt = [round(b - b0, 3) for b in beats]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    drop = a.get("drop") or bt[min(9, len(bt) - 1)]
    dur = round(drop + 3.4, 3)
    wd = tempfile.mkdtemp(prefix="news_")
    live = os.path.join(wd, "live.png"); lw, lh = build_live(live)
    chy = os.path.join(wd, "chy.png"); cw, ch = build_chyron(chy)
    pf = os.path.join(wd, "price.txt"); open(pf, "w", encoding="utf-8").write(PRICE)
    price_dt = E._drawtext(pf, int(H * 0.30), 170, E.RED, round(drop, 3), 10, "white@0.9")

    fc = ("[0:v]scale=1000:1300:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:(ow-iw)/2:250:color=white,setsar=1[bg];"
          f"[bg][1:v]overlay=60:120:enable='{E._esc(f'gte(t,{bt[1]})')}'[a];"
          f"[a][2:v]overlay=0:1360:enable='{E._esc(f'gte(t,{bt[2]})')}'[b];"
          f"[b]{price_dt},format=yuv420p")
    dur_s = f"{dur}"
    frames = int(round(dur * E.FPS)); seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", "-loop", "1", "-t", dur_s, "-i", _wb(*WATCH),
           "-loop", "1", "-t", dur_s, "-i", live, "-loop", "1", "-t", dur_s, "-i", chy,
           "-filter_complex", fc, "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s")


if __name__ == "__main__":
    main()
