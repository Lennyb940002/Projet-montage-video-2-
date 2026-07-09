# -*- coding: utf-8 -*-
"""Concept 'CHOC DE VALEUR' : montre au poignet passée pour du luxe (texte claim
qui monte) -> SUR LE DROP, cut vers la photo produit fond blanc + révélation prix
(Seiko mod 195€) + CTA. Même montre des deux côtés (aucun mismatch)."""
import os, sys, glob, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
WB_BASE = r"C:\Users\zbull\Downloads\montre fond blanc"

# ---- CONFIG -----------------------------------------------------------------
CLAIM_CLIP = r"C:\Users\zbull\Downloads\Royal Oak Or rose.mp4"     # poignet (KlingAI)
CROP_WM = 120                                                      # retire watermark bas
REVEAL_FOLDER = "Royal Oak"                                        # dossier fond blanc (même montre)
REVEAL_IMG_IDX = 0                                                 # rose gold
MUSIC = "05"                                                       # Diva (drop net)
CLAIM = [("Tout le monde", "white"), ("pense que c'est", "white"),
         ("une AP", "yellow"), ("à 40 000€", "yellow")]
PRICE = "195€"
SUB = "Seiko mod · NH35"
CTA = "LIEN EN BIO"
OUT_NAME = "reveal_test.mp4"
# -----------------------------------------------------------------------------


def _wb_image(sub, idx):
    folder = next(d for d in os.listdir(WB_BASE)
                  if os.path.isdir(os.path.join(WB_BASE, d)) and sub.lower() in d.lower())
    return sorted(glob.glob(os.path.join(WB_BASE, folder, "*.png")))[idx]


def render_claim(clip, start, dur, chunks, out, wd):
    files = E._write_textfiles(chunks, wd)
    sizes = [E._fit_size(c["text"], 120) for c in chunks]
    heights = [int(s * 1.15) for s in sizes]
    y = int(E.H * 0.09)
    dt = []
    for i, ch in enumerate(chunks):
        color = E.YELLOW if ch["color"] == "yellow" else E.WHITE
        dt.append(E._drawtext(files[i], y, sizes[i], color, ch["appear"], max(6, int(sizes[i] * 0.06))))
        y += heights[i]
    avail = E.probe_dur(clip) - start
    factor = max(1.0, dur / max(0.1, avail))            # ralentit pour remplir jusqu'au drop
    vf = (f"crop=iw:ih-{CROP_WM}:0:0,setpts={factor:.4f}*PTS,"
          "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
          + ",".join(dt) + ",format=yuv420p")
    frames = int(round(dur * E.FPS))
    E.run([E.FF, "-y", "-ss", f"{start}", "-i", clip, "-vf", vf,
           "-frames:v", str(frames), *E._X264, "-an", out])


def render_reveal(img, dur, out, wd):
    pp = os.path.join(wd, "r_price.txt"); open(pp, "w", encoding="utf-8").write(PRICE)
    ps = os.path.join(wd, "r_sub.txt"); open(ps, "w", encoding="utf-8").write(SUB)
    pc = os.path.join(wd, "r_cta.txt"); open(pc, "w", encoding="utf-8").write(CTA)
    yc = int(E.H * 0.63)                        # sous la montre : cadran dégagé
    dt = [
        E._drawtext(pp, yc, 205, E.RED, 0.12, borderw=8, border_color="white@0.9"),
        E._drawtext(ps, yc + 210, 58, E.INK, 0.24, borderw=4, border_color="white@0.8"),
        E._drawtext(pc, int(E.H * 0.90), 66, E.INK, max(0.2, dur - 2.2), borderw=4, border_color="white@0.85"),
    ]
    vf = ("scale=1000:1780:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1,"
          "fade=t=in:st=0:d=0.12:color=white,"                  # la montre surgit du flash
          + ",".join(dt) + ",format=yuv420p")
    frames = int(round(dur * E.FPS))
    E.run([E.FF, "-y", "-loop", "1", "-t", f"{dur}", "-i", img, "-vf", vf,
           "-frames:v", str(frames), *E._X264, "-an", out])


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    chunks = [{"text": t, "color": c, "size": 120} for (t, c) in CLAIM]
    chunks, intro_dur = E.plan_intro(chunks, beats, a.get("drop"))     # claim finit SUR le drop
    reveal_dur = 4.8
    wd = tempfile.mkdtemp(prefix="reveal_")
    claim = os.path.join(wd, "claim.mp4"); reveal = os.path.join(wd, "reveal.mp4")
    render_claim(CLAIM_CLIP, 0.2, intro_dur, chunks, claim, wd)
    render_reveal(_wb_image(REVEAL_FOLDER, REVEAL_IMG_IDX), reveal_dur, reveal, wd)
    visual = os.path.join(wd, "visual.mp4")
    E.concat([claim, reveal], visual, wd)
    vdur = E.probe_dur(visual)
    out = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(visual, music, 0.0, vdur, out)
    print(f"OK -> {out}  dur={vdur:.1f}s  claim={intro_dur:.1f}s (drop) + reveal={reveal_dur:.1f}s")


if __name__ == "__main__":
    main()
