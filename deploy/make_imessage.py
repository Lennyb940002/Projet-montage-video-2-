# -*- coding: utf-8 -*-
"""Concept FAUSSE CONVERSATION iMessage (mode sombre) : les bulles apparaissent
sur les beats, puis reveal montre + 195€ sur le drop. Faceless, très partageable."""
import os, sys, glob, tempfile, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"
FONT = r"C:\Windows\Fonts\arial.ttf"
FONTB = r"C:\Windows\Fonts\ariblk.ttf"
W, H = 1080, 1920
MUSIC = "07"
WATCH = ("Royal Oak", 0)
# (texte, côté)  l=reçu gris gauche, r=envoyé bleu droite
CONVO = [("c'est une vraie Rolex ???", "l"), ("nan c'est 195€", "r"),
         ("attends QUOI", "l"), ("Seiko mod. saphir + NH35", "r"),
         ("envoie le lien direct", "l")]
PRICE = "195€"
CTA = "Lien en bio"
OUT_NAME = "imessage_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def _wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textbbox((0, 0), t, font=font)[2] <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def build_bubble(text, side, out):
    f = ImageFont.truetype(FONT, 46)
    d0 = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines = _wrap(d0, text, f, 620)
    lh = 58; padx, pady = 34, 24
    tw = max(d0.textbbox((0, 0), ln, font=f)[2] for ln in lines)
    bw, bh = tw + 2 * padx, len(lines) * lh + 2 * pady
    P = 8
    img = Image.new("RGBA", (bw + 2 * P, bh + 2 * P), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = (58, 58, 60) if side == "l" else (11, 132, 246)
    d.rounded_rectangle([P, P, P + bw, P + bh], radius=bh // 2 if len(lines) == 1 else 42, fill=col)
    y = P + pady
    for ln in lines:
        d.text((P + padx, y), ln, font=f, fill=(255, 255, 255)); y += lh
    img.save(out)
    return img.width, img.height


def build_bg(out):
    t = np.linspace(0, 1, H)[:, None, None]
    bg = Image.fromarray((np.array([26, 26, 30]) * (1 - t) + np.array([6, 6, 8]) * t
                          ).astype("uint8").repeat(W, axis=1), "RGB")
    ImageDraw.Draw(bg).text((W / 2, 90), "iMessage", font=ImageFont.truetype(FONT, 40),
                            fill=(120, 120, 128), anchor="mm")
    bg.save(out)


def build_card(img, out):
    cw, ch, P = 520, 600, 40
    card = Image.new("RGBA", (cw, ch), (255, 255, 255, 255))
    w = Image.open(img).convert("RGBA"); w.thumbnail((cw - 50, ch - 50))
    card.alpha_composite(w, ((cw - w.width) // 2, (ch - w.height) // 2))
    m = Image.new("L", (cw, ch), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, cw, ch], 34, fill=255)
    card.putalpha(m)
    canvas = Image.new("RGBA", (cw + 2 * P, ch + 2 * P), (0, 0, 0, 0))
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([P, P + 14, P + cw, P + ch + 14], 34, fill=(0, 0, 0, 180))
    canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(24)))
    canvas.alpha_composite(card, (P, P))
    canvas.save(out)
    return canvas.width, canvas.height


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    bt = [round(b - b0, 3) for b in beats]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    drop = a.get("drop") or bt[min(9, len(bt) - 1)]
    wd = tempfile.mkdtemp(prefix="im_")
    bg = os.path.join(wd, "bg.png"); build_bg(bg)

    # placer les bulles empilées, apparition sur beats (avant le drop)
    inputs = ["-loop", "1", "-t", "1", "-i", bg]   # dur ajusté plus bas
    overlays = []
    y = 240
    for k, (text, side) in enumerate(CONVO):
        bp = os.path.join(wd, f"b{k}.png"); bw, bh = build_bubble(text, side, bp)
        x = 50 if side == "l" else (W - bw - 50)
        appear = bt[min(1 + k, len(bt) - 1)]
        overlays.append((bp, x, y, appear)); y += bh + 18
    # reveal montre + prix sur le drop
    card = os.path.join(wd, "card.png"); cw, ch = build_card(_wb(*WATCH), card)
    dur = round(drop + 3.6, 3)

    inp = ["-loop", "1", "-t", f"{dur}", "-i", bg]
    for (bp, _, _, _) in overlays:
        inp += ["-loop", "1", "-t", f"{dur}", "-i", bp]
    inp += ["-loop", "1", "-t", f"{dur}", "-i", card]

    fc = ""; prev = "0:v"
    for k, (bp, x, yy, appear) in enumerate(overlays):
        fc += f"[{prev}][{k+1}:v]overlay={x}:{yy}:enable='{E._esc(f'gte(t,{appear})')}'[o{k}];"
        prev = f"o{k}"
    ci = len(overlays) + 1
    cx, cy = (W - cw) // 2, int(H * 0.42)
    fc += f"[{prev}][{ci}:v]overlay={cx}:{cy}:enable='{E._esc(f'gte(t,{round(drop,3)})')}'[withcard];"
    # textes prix + CTA (drawtext) sur le drop
    pf = os.path.join(wd, "price.txt"); open(pf, "w", encoding="utf-8").write(PRICE)
    cf = os.path.join(wd, "cta.txt"); open(cf, "w", encoding="utf-8").write(CTA)
    price_dt = E._drawtext(pf, int(H * 0.80), 150, E.YELLOW, round(drop + 0.15, 3), 10)
    cta_dt = E._drawtext(cf, int(H * 0.90), 56, E.WHITE, round(drop + 0.4, 3), 5)
    fc += f"[withcard]{price_dt},{cta_dt},format=yuv420p"

    frames = int(round(dur * E.FPS)); seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", *inp, "-filter_complex", fc, "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  reveal@{drop:.1f}s")


if __name__ == "__main__":
    main()
