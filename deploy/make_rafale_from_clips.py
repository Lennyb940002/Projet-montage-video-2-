# -*- coding: utf-8 -*-
"""Monte 1 vidéo rafale (intro hook beat-syncé + N clips produit fournis) et la sort.
Recadre optionnellement le bas de chaque clip (retrait watermark).

Édite CLIPS / HOOK / MUSIC / PHOTO ci-dessous puis : python deploy/make_rafale_from_clips.py
"""
import os, sys, json, tempfile, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
BANK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "backend", "silent", "banks", "intro_streetwear")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
TARGET_DUR = 14.0

# ---- CONFIG (à éditer) ----------------------------------------------------
DL = r"C:\Users\zbull\Downloads"
CLIPS = [
    dict(src=os.path.join(DL, "Daytona Blue Saphire.mp4"), start=0.3, label="Daytona Saphir Bleu"),
    dict(src=os.path.join(DL, "Fuck 95 Santos.mp4"),       start=0.3, label="Santos"),
    dict(src=os.path.join(DL, "Royal Oak Or rose.mp4"),    start=0.4, label="Royal Oak Or Rose"),
]
CROP_BOTTOM = 120          # px retirés en bas de chaque clip (watermark KlingAI)
DROP_NUDGE = 0.0           # s : 0 = drop ET image au même instant. (+ = montre plus tard)
MUSIC = os.environ.get("RAFALE_MUSIC_KEY", "07")   # clé du son (voir _assets/music)
PHOTO = "intro_11.jpg"
HOOK = [
    ("Les", "white"), ("montres", "white"), ("incroyables", "yellow"),
    ("que presque", "white"), ("personne", "white"), ("ne connaît", "yellow"), ("part 1", "white"),
]
OUT_NAME = os.environ.get("RAFALE_OUT_NAME", "rafale_custom.mp4")
# ---------------------------------------------------------------------------


def precrop(src, out, bottom):
    """Retire 'bottom' px en bas (watermark), garde le haut."""
    w, h = _dims(src)
    subprocess.run([E.FF, "-y", "-i", src, "-vf", f"crop={w}:{h-bottom}:0:0",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                    "-an", out], check=True, capture_output=True, encoding="utf-8", errors="replace")


def _dims(src):
    out = subprocess.run([E.FP, "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", src],
                         capture_output=True, text=True).stdout.strip()
    w, h = out.split("x")[:2]
    return int(w), int(h)


def main():
    a = ANALYSIS[MUSIC]; beats = a["beats"]; b0 = beats[0]
    music = os.path.join(ASSETS, "music", f"{MUSIC}.wav")
    wd = tempfile.mkdtemp(prefix="rafc_")

    hook0 = [{"text": t, "color": c, "size": (44 if t.startswith("part") else 150)} for (t, c) in HOOK]
    hook, intro_dur = E.plan_intro(hook0, beats, a.get("drop"))   # cale sur le drop si détecté
    intro_dur = round(intro_dur + DROP_NUDGE, 3)                  # réglage fin de la frappe

    # coupes calées sur beats, N clips ~ égaux jusqu'à TARGET
    g = [round(b - b0, 3) for b in beats]
    n = len(CLIPS)
    span = TARGET_DUR - intro_dur
    bounds = [intro_dur]
    for j in range(1, n):
        tgt = intro_dur + span * j / n
        cand = min((x for x in g if x > bounds[-1] + 1.2), key=lambda x: abs(x - tgt), default=tgt)
        bounds.append(round(cand, 3))
    bounds.append(round(TARGET_DUR, 3))

    intro = os.path.join(wd, "intro.mp4")
    E.render_intro(os.path.join(BANK, PHOTO), hook, intro, intro_dur, wd)
    parts = [intro]
    for k, c in enumerate(CLIPS):
        src = c["src"]
        if CROP_BOTTOM:
            cropped = os.path.join(wd, f"crop_{k}.mp4")
            precrop(src, cropped, CROP_BOTTOM)
            src = cropped
        seg = round(max(1.8, bounds[k + 1] - bounds[k]), 3)
        out = os.path.join(wd, f"seg_{k+1}.mp4")
        E.render_clip(src, c["start"], seg, c["label"], "", out, wd, k + 1, zoom=True)
        parts.append(out)

    visual = os.path.join(wd, "visual.mp4")
    E.concat(parts, visual, wd)
    vdur = E.probe_dur(visual)
    final = os.path.join(OUT_DIR, OUT_NAME)
    E.add_music(visual, music, 0.0, vdur, final)
    print(f"OK -> {final}  dur={vdur:.1f}s  intro={intro_dur:.1f}s  clips={n}  musique={a['name']}")


if __name__ == "__main__":
    main()
