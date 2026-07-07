# -*- coding: utf-8 -*-
"""Monte 1 vidéo = INTRO (photo + hook beat-syncé) + 1 PRISE fournie (ex. 4 montres),
musique par-dessus. Réutilise rafale_engine + les assets persistants.

Usage : python deploy/make_choix_video.py [chemin_video] [cle_musique] [intro.jpg]
Défauts : la prise 'Nouveau dossier (2)', musique DAME UN GRR, intro_20.
"""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
BANK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "backend", "silent", "banks", "intro_streetwear")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))

REC = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\zbull\Downloads\Nouveau dossier (2)\watermark_removed_958b770d-eb74-4971-b0cf-ded7b603b9bf.mp4"
MKEY = sys.argv[2] if len(sys.argv) > 2 else "01"       # DAME UN GRR
PHOTO = os.path.join(BANK, sys.argv[3] if len(sys.argv) > 3 else "intro_20.jpg")

# hook "choisis ta préférée" (4 montres à comparer)
HOOK = [
    {"text": "Les", "color": "white", "size": 150},
    {"text": "montres", "color": "white", "size": 150},
    {"text": "du moment", "color": "yellow", "size": 150},
    {"text": "choisis", "color": "white", "size": 150},
    {"text": "ta préférée", "color": "yellow", "size": 150},
    {"text": "part 1", "color": "white", "size": 44},
]


def main():
    a = ANALYSIS[MKEY]
    beats = a["beats"]; b0 = beats[0]
    music = os.path.join(ASSETS, "music", f"{MKEY}.wav")
    rec_dur = E.probe_dur(REC)

    hook = [dict(c) for c in HOOK]
    for i, c in enumerate(hook):
        c["appear"] = round(beats[min(i, len(beats) - 1)] - b0, 3)
    # pause ~1,2 s puis la prise entre sur un temps fort (index pair)
    lo = hook[-1]["appear"] + 1.2
    bi = next((i for i in range(len(beats)) if i % 2 == 0 and beats[i] - b0 >= lo), None)
    if bi is None:
        bi = next((i for i in range(len(beats)) if beats[i] - b0 >= lo), len(beats) - 1)
    intro_dur = round(beats[bi] - b0, 3)

    wd = tempfile.mkdtemp(prefix="choix_")
    intro = os.path.join(wd, "intro.mp4")
    clip = os.path.join(wd, "clip.mp4")
    E.render_intro(PHOTO, hook, intro, intro_dur, wd)
    # prise plein cadre, SANS zoom (on garde le mouvement de la main), sans label
    E.render_clip(REC, 0.0, rec_dur, "", "", clip, wd, 1, zoom=False)
    visual = os.path.join(wd, "visual.mp4")
    E.concat([intro, clip], visual, wd)
    vdur = E.probe_dur(visual)
    out = os.path.join(OUT_DIR, "rafale_choix.mp4")
    E.add_music(visual, music, 0.0, vdur, out)
    print(f"OK -> {out}  dur={vdur:.1f}s  (intro {intro_dur:.1f}s + prise {rec_dur:.1f}s)  "
          f"musique={a['name']}")


if __name__ == "__main__":
    main()
