# -*- coding: utf-8 -*-
"""Concept THIS OR THAT (rendu premium PIL) : 2 cartes montres avec ombre, badges
1/2, un 'VS' qui claque sur le drop, fond sombre. CTA 'COMMENTE 1 OU 2'."""
import os, sys, glob, tempfile, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"
FONT = r"C:\Windows\Fonts\ariblk.ttf"
W, H = 1080, 1920
PAD = 44
TOP = ("Daytona", 0); BOTTOM = ("Santos", 1)
MUSIC = "01"
OUT_NAME = "thisorthat_test.mp4"
CARD_W, CARD_H = 620, 640
POS1 = (230, 250); POS2 = (230, 1030)     # coins visuels des cartes


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def _rounded(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return m


def build_base(out):
    t = np.linspace(0, 1, H)[:, None, None]
    bg = Image.fromarray((np.array([28, 28, 34]) * (1 - t) + np.array([12, 12, 15]) * t
                          ).astype("uint8").repeat(W, axis=1), "RGB")
    d = ImageDraw.Draw(bg)
    d.text((W / 2, 120), "TU PRENDS LAQUELLE ?", font=ImageFont.truetype(FONT, 66),
           fill=(255, 255, 255), anchor="mm")
    d.text((W / 2, 1852), "COMMENTE 1 OU 2", font=ImageFont.truetype(FONT, 60),
           fill=(255, 214, 92), anchor="mm")
    bg.save(out)


def build_card(watch, number, accent, out):
    card = Image.new("RGBA", (CARD_W, CARD_H), (255, 255, 255, 255))
    w = Image.open(watch).convert("RGBA"); w.thumbnail((CARD_W - 60, CARD_H - 60))
    card.alpha_composite(w, ((CARD_W - w.width) // 2, (CARD_H - w.height) // 2))
    card.putalpha(_rounded(CARD_W, CARD_H, 34))
    canvas = Image.new("RGBA", (CARD_W + 2 * PAD, CARD_H + 2 * PAD), (0, 0, 0, 0))
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([PAD, PAD + 14, PAD + CARD_W, PAD + CARD_H + 14],
                                         radius=34, fill=(0, 0, 0, 160))
    canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(22)))
    canvas.alpha_composite(card, (PAD, PAD))
    # badge numéro
    d = ImageDraw.Draw(canvas); bx, by, r = PAD + 8, PAD + 8, 66
    d.ellipse([bx, by, bx + 2 * r, by + 2 * r], fill=accent)
    d.text((bx + r, by + r), str(number), font=ImageFont.truetype(FONT, 78), fill=(255, 255, 255), anchor="mm")
    canvas.save(out)


def build_vs(out):
    S = 260
    c = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.ellipse([10, 10, S - 10, S - 10], fill=(224, 16, 43), outline=(255, 255, 255), width=8)
    d.text((S / 2, S / 2 - 6), "VS", font=ImageFont.truetype(FONT, 120), fill=(255, 255, 255), anchor="mm")
    c.save(out)


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    bt = [round(b - b0, 3) for b in beats]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    drop = a.get("drop") or bt[min(8, len(bt) - 1)]
    b1, b2 = bt[min(2, len(bt) - 1)], bt[min(4, len(bt) - 1)]
    dur = round(drop + 3.2, 3)
    wd = tempfile.mkdtemp(prefix="tot_")
    base = os.path.join(wd, "base.png"); build_base(base)
    c1 = os.path.join(wd, "c1.png"); build_card(_wb(*TOP), 1, (59, 130, 246), c1)
    c2 = os.path.join(wd, "c2.png"); build_card(_wb(*BOTTOM), 2, (245, 158, 11), c2)
    vs = os.path.join(wd, "vs.png"); build_vs(vs)

    inp = ["-loop", "1", "-t", f"{dur}", "-i", base,
           "-loop", "1", "-t", f"{dur}", "-i", c1,
           "-loop", "1", "-t", f"{dur}", "-i", c2,
           "-loop", "1", "-t", f"{dur}", "-i", vs]
    e = lambda x: E._esc(f"gte(t,{x})")
    fc = (f"[0:v][1:v]overlay={POS1[0]-PAD}:{POS1[1]-PAD}:enable='{e(b1)}'[a];"
          f"[a][2:v]overlay={POS2[0]-PAD}:{POS2[1]-PAD}:enable='{e(b2)}'[b];"
          f"[b][3:v]overlay=(W-w)/2:(H-h)/2:enable='{e(round(drop,3))}'[c];"
          "[c]format=yuv420p")
    frames = int(round(dur * E.FPS)); seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", *inp, "-filter_complex", fc, "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  cartes@{b1},{b2}  VS@{drop:.1f}s")


if __name__ == "__main__":
    main()
