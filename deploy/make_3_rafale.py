# -*- coding: utf-8 -*-
"""Driver : rend les 3 vidéos 'selection_rafale' beat-syncées et rapporte les chemins.

- Lit l'analyse musicale (fenêtre 16s + beats) depuis RAFALE_ASSETS/analysis.json.
- Mappe les beats -> apparition des mots (intro) et coupes des clips (rafale).
- Sort les .mp4 dans OUT_DIR.

Usage : python deploy/make_3_rafale.py [1|2|3|all]
"""
import os, sys, json, glob, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy import rafale_engine as E

# Chemins (surchargeables par variables d'env pour tourner sur un autre PC).
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.environ.get("RAFALE_ASSETS", r"C:\Users\zbull\Downloads\rafale_out\_assets")
MUSIC_DIR = os.path.join(ASSETS, "music")          # {key}.wav (segments 16s calés beat)
NOTUBE = os.environ.get("RAFALE_NOTUBE", r"C:\Users\zbull\Downloads\noTube")
BANK = os.path.join(_REPO, "backend", "silent", "banks", "intro_streetwear")
OUT_DIR = os.environ.get("RAFALE_OUT", r"C:\Users\zbull\Downloads\rafale_out")
os.makedirs(OUT_DIR, exist_ok=True)

TARGET_DUR = 15.0  # durée cible (10-15 s max)

ANALYSIS = json.load(open(os.path.join(ASSETS, "analysis.json"), encoding="utf-8"))
_mp4 = sorted(glob.glob(os.path.join(NOTUBE, "*.mp4")))

# index (1-based tri alpha) -> (fichier, start hero, label modèle)
WATCH = {
    1: (_mp4[0], 4.0,  "AP Royal Oak Bleu"),
    2: (_mp4[1], 6.0,  "GMT Batman"),
    3: (_mp4[2], 1.6,  "Daytona Rainbow"),
    # 4 = Patek (watermark TikTok) -> exclu
    5: (_mp4[4], 3.2,  "Daytona Chocolat"),
    6: (_mp4[5], 7.5,  "Datejust Wimbledon"),
    7: (_mp4[6], 1.6,  "Marin Master"),
    8: (_mp4[7], 5.5,  "Or Rose Mod"),
    9: (_mp4[8], 3.0,  "Royal Oak Bleu"),
}
PRICE = "194,90 €"

BIG, SMALL = 150, 44  # 'size' = plafond ; le moteur agrandit chaque mot pour remplir la largeur

def chunks(spec):
    """spec: list of (text, color). Mots courts -> chacun remplit la page."""
    return [{"text": t, "color": c, "size": (SMALL if t.startswith("part") else BIG)}
            for (t, c) in spec]

HOOK_A = chunks([
    ("Les", "white"), ("montres", "white"), ("incroyables", "yellow"),
    ("que presque", "white"), ("personne", "white"), ("ne connaît", "yellow"), ("part 1", "white"),
])
HOOK_B = chunks([
    ("Les", "white"), ("montres", "white"), ("sous-cotées", "yellow"),
    ("qui font", "white"), ("vraiment", "white"), ("la diff", "yellow"), ("part 1", "white"),
])
HOOK_C = chunks([
    ("Les", "white"), ("meilleures", "yellow"), ("montres", "white"),
    ("à avoir", "white"), ("absolument", "yellow"), ("cet été", "yellow"), ("part 1", "white"),
])

RECIPES = {
    1: dict(music="05", photo="intro_02.jpg", hook=HOOK_A, order=[9, 6, 3]),
    2: dict(music="07", photo="intro_09.jpg", hook=HOOK_B, order=[1, 5, 2]),
    3: dict(music="01", photo="intro_16.jpg", hook=HOOK_C, order=[6, 9, 8]),
}


def build(idx):
    r = RECIPES[idx]
    a = ANALYSIS[r["music"]]
    beats = a["beats"]
    music_wav = os.path.join(MUSIC_DIR, f"{r['music']}.wav")

    # ---- intro : 1 mot par beat, le 1er mot PILE sur le beat fort (t=0) ----
    hook = [dict(c) for c in r["hook"]]
    nb = len(hook)
    b0 = beats[0]
    for i, c in enumerate(hook):
        c["appear"] = round(beats[min(i, len(beats) - 1)] - b0, 3)
    # pause ~1,2-1,7 s après le dernier mot, puis 1re montre sur un TEMPS FORT (le drop)
    last_word = hook[-1]["appear"]
    lo = last_word + 1.2
    bi = next((i for i in range(len(beats)) if i % 2 == 0 and (beats[i] - b0) >= lo), None)
    if bi is None:
        bi = next((i for i in range(len(beats)) if (beats[i] - b0) >= lo), len(beats) - 1)
    intro_dur = round(beats[bi] - b0, 3)

    # ---- rafale : 2-3 montres, coupes calées sur beats, chacune longue ----
    g = [round(b - b0, 3) for b in beats]
    n = min(len(r["order"]), 3)
    span = TARGET_DUR - intro_dur
    bounds = [intro_dur]
    for j in range(1, n):
        tgt = intro_dur + span * j / n
        cand = min((b for b in g if b > bounds[-1] + 1.2), key=lambda b: abs(b - tgt), default=tgt)
        bounds.append(round(cand, 3))
    bounds.append(round(TARGET_DUR, 3))
    clips = []
    for k in range(n):
        seg = round(max(1.8, bounds[k + 1] - bounds[k]), 3)
        wf, wstart, wlabel = WATCH[r["order"][k]]
        clips.append(dict(src=wf, start=wstart, seg=seg, top=wlabel, price=""))

    recipe = dict(
        photo=os.path.join(BANK, r["photo"]),
        hook_chunks=hook, intro_dur=round(intro_dur, 3),
        clips=clips, music=music_wav, music_start=a["win_start"],
    )
    out = os.path.join(OUT_DIR, f"rafale_{idx}_{a['name'].split(' ')[0].lower()}.mp4")
    path, vdur = E.build_video(recipe, out)
    print(f"VIDEO {idx}: {os.path.basename(path)}  dur={vdur:.1f}s  "
          f"intro={intro_dur:.1f}s  clips={len(clips)}  music={a['name']} @ {a['win_start']}s")
    # dump timing pour vérif sync (cuts == beats)
    cut_ts, t = [round(intro_dur, 2)], intro_dur
    for c in clips:
        t += c["seg"]; cut_ts.append(round(t, 2))
    print(f"   coupes (s): {cut_ts}")
    return path


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    ids = [int(which)] if which != "all" else [1, 2, 3]
    for i in ids:
        build(i)
