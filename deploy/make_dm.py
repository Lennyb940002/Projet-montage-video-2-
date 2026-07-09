# -*- coding: utf-8 -*-
"""Générateur générique 'concept DM' : montre fond blanc + hook qui monte +
BADGE CTA DM qui pop sur le drop (comment-to-DM). Config via globals (monkeypatch)."""
import os, sys, glob, tempfile, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"
FONT = r"C:\Windows\Fonts\ariblk.ttf"

# ---- CONFIG (monkeypatch) ---------------------------------------------------
WATCH = ("Royal Oak", 0)
HOOK = [("Le prix de", "ink"), ("cette montre", "ink"), ("va te choquer", "red")]
CTA = "Commente PRIX"
CTA_COLOR = (37, 211, 102)
MUSIC = "05"
OUT_NAME = "dm_test.mp4"
# -----------------------------------------------------------------------------


def _wb(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def build_pill(text, out, bg):
    f = ImageFont.truetype(FONT, 66)
    d0 = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tw = d0.textbbox((0, 0), text, font=f)[2]
    pad, h = 60, 138
    w = tw + 2 * pad
    P = 40
    canvas = Image.new("RGBA", (w + 2 * P, h + 2 * P), (0, 0, 0, 0))
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([P, P + 12, P + w, P + h + 12], radius=h // 2, fill=(0, 0, 0, 150))
    canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(20)))
    pill = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle([0, 0, w, h], radius=h // 2, fill=bg + (255,))
    ImageDraw.Draw(pill).text((w // 2, h // 2 - 4), text, font=f, fill=(255, 255, 255), anchor="mm")
    canvas.alpha_composite(pill, (P, P))
    canvas.save(out)
    return canvas.width, canvas.height


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    chunks = [{"text": t, "color": c, "size": 118} for (t, c) in HOOK]
    chunks, drop = E.plan_intro(chunks, beats, a.get("drop"))
    dur = round(drop + 3.4, 3)
    wd = tempfile.mkdtemp(prefix="dm_")
    pill = os.path.join(wd, "pill.png"); pw, ph = build_pill(CTA, pill, CTA_COLOR)

    files = E._write_textfiles(chunks, wd)
    sizes = [E._fit_size(c["text"], 118) for c in chunks]
    heights = [int(s * 1.14) for s in sizes]; y = int(E.H * 0.06); dt = []
    for i, ch in enumerate(chunks):
        color = E.RED if ch["color"] == "red" else E.INK
        dt.append(E._drawtext(files[i], y, sizes[i], color, ch["appear"], 5, "white@0.85"))
        y += heights[i]
    frames = int(round(dur * E.FPS))
    px, py = (E.W - pw) // 2, int(E.H * 0.80) - ph // 2
    fc = ("[0:v]scale=960:1360:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:(ow-iw)/2:150:color=white,setsar=1,"
          + ",".join(dt) + f"[b];[b][1:v]overlay={px}:{py}:enable='{E._esc(f'gte(t,{round(drop,3)})')}',format=yuv420p")
    seg = os.path.join(wd, "seg.mp4")
    E.run([E.FF, "-y", "-loop", "1", "-t", f"{dur}", "-i", _wb(*WATCH),
           "-loop", "1", "-t", f"{dur}", "-i", pill, "-filter_complex", fc,
           "-frames:v", str(frames), *E._X264, "-an", seg])
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(seg, music, 0.0, E.probe_dur(seg), out)
    print(f"OK -> {out}  dur={E.probe_dur(out):.1f}s  CTA@{drop:.1f}s")


if __name__ == "__main__":
    main()
