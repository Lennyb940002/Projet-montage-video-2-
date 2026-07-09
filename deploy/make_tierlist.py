# -*- coding: utf-8 -*-
"""Concept TIER LIST (rendu premium PIL) : fond sombre, rangées S/A/B en dégradé
arrondi, cartes montres avec ombre. Les montres se placent sur le beat.
Debate-bait : « TU METS QUOI EN S ? »."""
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
MUSIC = "21"
W, H = 1080, 1920
PAD = 40                                   # marge ombre autour des cartes
ROWS = [("S", (232, 185, 40), (255, 214, 92), 330),
        ("A", (150, 158, 172), (200, 208, 222), 840),
        ("B", (192, 132, 82), (222, 168, 112), 1350)]
ROW_H, MARGIN = 470, 40
# (montre, idx, ligne S/A/B, x visuel, y visuel)
PLACE = [("Royal Oak", 0, 0, 330, 355), ("Daytona", 0, 0, 705, 355),
         ("Datejust", 0, 1, 330, 865), ("Santos", 1, 2, 330, 1375)]
CARD_W, CARD_H = 350, 420
OUT_NAME = "tierlist_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def _hgrad(w, h, c1, c2):
    t = np.linspace(0, 1, w)[None, :, None]
    arr = (np.array(c1)[None, None, :] * (1 - t) + np.array(c2)[None, None, :] * t).astype("uint8")
    return Image.fromarray(np.repeat(arr, h, axis=0), "RGB")


def _rounded(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return m


def build_base(out):
    # fond dégradé sombre
    t = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([30, 30, 36]), np.array([12, 12, 15])
    bg = Image.fromarray((top * (1 - t) + bot * t).astype("uint8").repeat(W, axis=1), "RGB").convert("RGBA")
    d = ImageDraw.Draw(bg)
    ft = ImageFont.truetype(FONT, 118); fs = ImageFont.truetype(FONT, 46); fb = ImageFont.truetype(FONT, 52)
    d.text((W / 2, 95), "TIER LIST", font=ft, fill=(255, 255, 255), anchor="mm")
    d.text((W / 2, 195), "LE CLASSEMENT FLEX", font=fs, fill=(255, 214, 92), anchor="mm")
    d.text((W / 2, 1870), "TU METS QUOI EN S ?", font=fb, fill=(255, 255, 255), anchor="mm")
    fL = ImageFont.truetype(FONT, 150)
    for (letter, c1, c2, ry) in ROWS:
        bar = _hgrad(1000, ROW_H, c1, c2).convert("RGBA")
        bar.putalpha(_rounded(1000, ROW_H, 46))
        # ombre douce de la barre
        sh = Image.new("RGBA", (W, ROW_H + 40), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([MARGIN, 16, MARGIN + 1000, ROW_H + 16], radius=46, fill=(0, 0, 0, 130))
        bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (0, ry - 8))
        bg.alpha_composite(bar, (MARGIN, ry))
        # badge lettre
        d.text((MARGIN + 120, ry + ROW_H / 2), letter, font=fL, fill=(20, 20, 24), anchor="mm")
    bg.convert("RGB").save(out)


def build_card(watch, out):
    card = Image.new("RGBA", (CARD_W, CARD_H), (255, 255, 255, 255))
    w = Image.open(watch).convert("RGBA"); w.thumbnail((CARD_W - 44, CARD_H - 44))
    card.alpha_composite(w, ((CARD_W - w.width) // 2, (CARD_H - w.height) // 2))
    card.putalpha(_rounded(CARD_W, CARD_H, 30))
    canvas = Image.new("RGBA", (CARD_W + 2 * PAD, CARD_H + 2 * PAD), (0, 0, 0, 0))
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([PAD, PAD + 12, PAD + CARD_W, PAD + CARD_H + 12], radius=30, fill=(0, 0, 0, 150))
    canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(20)))
    canvas.alpha_composite(card, (PAD, PAD))
    canvas.save(out)


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    bt = [round(b - b0, 3) for b in beats]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    wd = tempfile.mkdtemp(prefix="tier_")
    base = os.path.join(wd, "base.png"); build_base(base)
    cards = []
    for k, (sub, idx, row, x, y) in enumerate(PLACE):
        c = os.path.join(wd, f"card{k}.png"); build_card(_wb(sub, idx), c)
        cards.append((c, x - PAD, y - PAD))
    place_beats = [bt[min(4 + 2 * k, len(bt) - 1)] for k in range(len(cards))]
    dur = round(place_beats[-1] + 2.2, 3)

    inputs = ["-loop", "1", "-t", f"{dur}", "-i", base]
    for c, _, _ in cards:
        inputs += ["-loop", "1", "-t", f"{dur}", "-i", c]
    fc = ""; prev = "0:v"
    for k, (c, x, y) in enumerate(cards):
        en = E._esc(f"gte(t,{place_beats[k]})")
        fc += f"[{prev}][{k+1}:v]overlay={x}:{y}:enable='{en}'[o{k}];"
        prev = f"o{k}"
    fc += f"[{prev}]format=yuv420p"
    frames = int(round(dur * E.FPS))
    seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", *inputs, "-filter_complex", fc, "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  placements@{place_beats}")


if __name__ == "__main__":
    main()
