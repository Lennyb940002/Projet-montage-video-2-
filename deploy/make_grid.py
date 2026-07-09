# -*- coding: utf-8 -*-
"""Concept LE CALCUL ABSURDE : une grille de montres se remplit sur les beats ->
'pour 1 Rolex (40 000€) = 205 montres'. Ancrage rendu visuel."""
import os, sys, glob, tempfile, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"
FONT = r"C:\Windows\Fonts\ariblk.ttf"
W, H = 1080, 1920
MUSIC = "21"
MODELS = [("Royal Oak", 0), ("Daytona", 0), ("Datejust", 0), ("Santos", 1)]
COLS, ROWS = 5, 4
OUT_NAME = "grid_test.mp4"


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def build_bg(out):
    t = np.linspace(0, 1, H)[:, None, None]
    bg = Image.fromarray((np.array([24, 24, 28]) * (1 - t) + np.array([8, 8, 10]) * t
                          ).astype("uint8").repeat(W, axis=1), "RGB")
    bg.save(out)


def build_row(imgs, out):
    cw, ch, gap = 176, 216, 16
    Wr = COLS * cw + (COLS - 1) * gap
    strip = Image.new("RGBA", (Wr, ch), (0, 0, 0, 0))
    for i, im in enumerate(imgs):
        card = Image.new("RGBA", (cw, ch), (255, 255, 255, 255))
        w = Image.open(im).convert("RGBA"); w.thumbnail((cw - 24, ch - 24))
        card.alpha_composite(w, ((cw - w.width) // 2, (ch - w.height) // 2))
        m = Image.new("L", (cw, ch), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, cw, ch], 20, fill=255)
        card.putalpha(m)
        strip.alpha_composite(card, (i * (cw + gap), 0))
    strip.save(out)
    return strip.size


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    bt = [round(b - b0, 3) for b in beats]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    wd = tempfile.mkdtemp(prefix="grid_")
    bg = os.path.join(wd, "bg.png"); build_bg(bg)
    imgs = [_wb(*m) for m in MODELS]
    rows = []
    for r in range(ROWS):
        row_imgs = [imgs[(r * COLS + c) % len(imgs)] for c in range(COLS)]
        rp = os.path.join(wd, f"row{r}.png"); rw, rh = build_row(row_imgs, rp)
        rows.append((rp, rw, rh))
    row_beats = [bt[min(2 + r, len(bt) - 1)] for r in range(ROWS)]
    drop = a.get("drop") or bt[min(9, len(bt) - 1)]
    drop = max(drop, row_beats[-1] + 0.6)
    dur = round(drop + 3.0, 3)

    x0 = (W - rows[0][1]) // 2
    y0 = 420; gapy = rows[0][2] + 22
    inp = ["-loop", "1", "-t", f"{dur}", "-i", bg]
    for (rp, _, _) in rows:
        inp += ["-loop", "1", "-t", f"{dur}", "-i", rp]
    fc = ""; prev = "0:v"
    for r, (rp, rw, rh) in enumerate(rows):
        fc += f"[{prev}][{r+1}:v]overlay={x0}:{y0 + r * gapy}:enable='{E._esc(f'gte(t,{row_beats[r]})')}'[o{r}];"
        prev = f"o{r}"
    tf = os.path.join(wd, "top.txt"); open(tf, "w", encoding="utf-8").write("Pour 1 Rolex à 40 000€…")
    pf = os.path.join(wd, "p.txt"); open(pf, "w", encoding="utf-8").write("= 205 montres")
    top_dt = E._drawtext(tf, 150, 62, E.WHITE, bt[1], 5)
    punch_dt = E._drawtext(pf, int(H * 0.80), 110, E.YELLOW, round(drop, 3), 8)
    fc += f"[{prev}]{top_dt},{punch_dt},format=yuv420p"
    frames = int(round(dur * E.FPS)); seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", *inp, "-filter_complex", fc, "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s")


if __name__ == "__main__":
    main()
