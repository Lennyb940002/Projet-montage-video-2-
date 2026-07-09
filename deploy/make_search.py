# -*- coding: utf-8 -*-
"""Concept BARRE DE RECHERCHE : on tape 'Rolex prix' -> 40 000€ -> '195€ ?' + montre.
Format meme search-bar, très reconnaissable."""
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
WATCH = ("Royal Oak", 0)
MUSIC = "39"
QUERY = "Rolex Daytona prix"
RESULT = "≈ 40 000 €"
OUT_NAME = "search_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def build_bar(out):
    Wb, Hb = 960, 130
    img = Image.new("RGBA", (Wb, Hb), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, Wb, Hb], Hb // 2, fill=(255, 255, 255), outline=(210, 210, 210), width=3)
    d.ellipse([44, 44, 90, 90], outline=(120, 120, 120), width=7)          # loupe
    d.line([86, 86, 110, 110], fill=(120, 120, 120), width=7)
    d.text((150, Hb // 2), QUERY, font=ImageFont.truetype(FONTR, 50), fill=(40, 40, 40), anchor="lm")
    img.save(out); return Wb, Hb


def build_card(img, out):
    cw, ch, P = 520, 600, 36
    from PIL import ImageFilter
    card = Image.new("RGBA", (cw, ch), (255, 255, 255, 255))
    w = Image.open(img).convert("RGBA"); w.thumbnail((cw - 50, ch - 50))
    card.alpha_composite(w, ((cw - w.width) // 2, (ch - w.height) // 2))
    m = Image.new("L", (cw, ch), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, cw, ch], 30, fill=255)
    card.putalpha(m)
    canvas = Image.new("RGBA", (cw + 2 * P, ch + 2 * P), (0, 0, 0, 0))
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([P, P + 12, P + cw, P + ch + 12], 30, fill=(0, 0, 0, 120))
    canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(20)))
    canvas.alpha_composite(card, (P, P))
    canvas.save(out); return canvas.width, canvas.height


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    bt = [round(b - b0, 3) for b in beats]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    drop = a.get("drop") or bt[min(9, len(bt) - 1)]
    dur = round(drop + 3.4, 3)
    wd = tempfile.mkdtemp(prefix="srch_")
    bar = os.path.join(wd, "bar.png"); bw, bh = build_bar(bar)
    card = os.path.join(wd, "card.png"); cw, ch = build_card(_wb(*WATCH), card)

    rf = os.path.join(wd, "res.txt"); open(rf, "w", encoding="utf-8").write(RESULT)
    qf = os.path.join(wd, "q.txt"); open(qf, "w", encoding="utf-8").write("et si je te disais…")
    pf = os.path.join(wd, "p.txt"); open(pf, "w", encoding="utf-8").write("195€")
    res_dt = E._drawtext(rf, 360, 150, E.RED, bt[2], 8, "white@0.9")
    q_dt = E._drawtext(qf, 640, 56, E.INK, round(drop - 0.6, 3), 4, "white@0.85")
    price_dt = E._drawtext(pf, int(H * 0.82), 160, "#0FA958", round(drop, 3), 10, "white@0.9")

    cx, cy = (W - cw) // 2, int(H * 0.44)
    fc = ("color=white:s=1080x1920,setsar=1[bg];"
          f"[bg][1:v]overlay=(W-w)/2:130:enable='{E._esc(f'gte(t,{bt[1]})')}'[a];"
          f"[a]{res_dt},{q_dt}[b];"
          f"[b][2:v]overlay={cx}:{cy}:enable='{E._esc(f'gte(t,{round(drop,3)})')}'[c];"
          f"[c]{price_dt},format=yuv420p")
    frames = int(round(dur * E.FPS)); seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", "-f", "lavfi", "-t", f"{dur}", "-i", "color=white:s=1080x1920",
           "-loop", "1", "-t", f"{dur}", "-i", bar, "-loop", "1", "-t", f"{dur}", "-i", card,
           "-filter_complex", fc, "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s")


if __name__ == "__main__":
    main()
