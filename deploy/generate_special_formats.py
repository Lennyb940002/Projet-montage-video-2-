"""Générateur de lot pour les formats spéciaux industrialisés :
- 'choix_4'    : grille 2x2 (4 tuiles) sur fond vidéo + 4 CTA d'action.
- 'devine_prix': 1 montre (clip), devine -> suspense -> reveal prix -> CTA.
Banques + anti-répétition (quatuors/montres uniques, hooks <=2, CTA rotation).
NE POSTE RIEN. Sortie : output/special_formats/ + manifest.json."""
import os
import sys
import glob
import json
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.silent import special_render as sr
from backend.config import SILENT

W, H = sr.W, sr.H
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output", "special_formats")
TILES = r"C:\Users\User\Desktop\Catalogue montre\_flowers_tiles"
BG_DIR = os.path.join(ROOT, "Vidéo montage fond")
CLIPS = SILENT["clips_dir"]
PRIX = "194,90 €"   # vrai prix (tuiles) — reveal honnête ; à changer si besoin

HOOKS_CHOIX = ["Tu choisis laquelle ?", "Ta préférée ?", "1, 2, 3 ou 4 ?",
               "Laquelle au poignet ?", "Tu prends laquelle ?"]
ACTIONS = ["LIKE = 1", "PARTAGE = 2", "COMMENTE = 3", "ENREGISTRE = 4"]
HOOKS_DEVINE = ["Devine le prix de cette montre", "Tu paierais combien ?",
                "Ça coûte combien à ton avis ?"]
CTA_DEVINE = ["T'aurais dit combien ?", "Tu pensais à combien ?", "Trop cher ou pas ?"]


def _tiles_by_model():
    out = {}
    for d in sorted(glob.glob(os.path.join(TILES, "*"))):
        if os.path.isdir(d):
            pngs = sorted(glob.glob(os.path.join(d, "*.png")))
            if pngs:
                out[os.path.basename(d)] = pngs
    return out


def _clips():
    return sorted(glob.glob(os.path.join(CLIPS, "*", "*.mp4")))


def _pick_hook(bank, used, rng):
    fresh = [h for h in bank if used.get(h, 0) < 2] or bank
    h = rng.choice(fresh)
    used[h] = used.get(h, 0) + 1
    return h


def build_choix(n, rng):
    models = _tiles_by_model()
    bg = sorted(glob.glob(os.path.join(BG_DIR, "*.mp4")))[0]
    used_hooks, used_quatuors, plan = {}, set(), []
    for _ in range(n):
        for _try in range(40):
            four = rng.sample(list(models), 4)
            key = frozenset(four)
            if key in used_quatuors:
                continue
            used_quatuors.add(key)
            break
        tiles = [rng.choice(models[m]) for m in four]
        plan.append({"hook": _pick_hook(HOOKS_CHOIX, used_hooks, rng),
                     "tiles": tiles, "models": four, "bg": bg})
    return plan


def build_devine(n, rng):
    clips = _clips()
    used_hooks, used_cta, used_clips, plan = {}, {}, set(), []
    for _ in range(n):
        pool = [c for c in clips if c not in used_clips] or clips
        clip = rng.choice(pool)
        used_clips.add(clip)
        plan.append({"hook": _pick_hook(HOOKS_DEVINE, used_hooks, rng),
                     "clip": clip, "prix": PRIX,
                     "cta": _pick_hook(CTA_DEVINE, used_cta, rng)})
    return plan


def _render_devine(item, out):
    top = f"\\an8\\pos({W // 2},210)"
    center = f"\\an5\\pos({W // 2},{H // 2})"
    sr.render_sequence([
        {"kind": "visual", "path": item["clip"],
         "events": [(item["hook"], "Big", top)], "dur": 1.5},
        {"kind": "visual", "path": item["clip"],
         "events": [("Trop haut ?   Trop bas ?", "Big", top)], "dur": 1.3},
        {"kind": "visual", "path": item["clip"],
         "events": [(item["prix"], "Huge", center)], "dur": 1.7},
        {"kind": "text", "events": [(item["cta"], "Big", center)], "dur": 1.3},
    ], out)


def manifest_choix(item, out):
    return {"concept": "choix_4", "hook": item["hook"], "montres": item["models"],
            "tiles": item["tiles"], "actions": ACTIONS, "export": out,
            "nouveau_rendu": "grille 2x2 sur fond video"}


def manifest_devine(item, out):
    return {"concept": "devine_prix", "hook": item["hook"],
            "montre": os.path.basename(os.path.dirname(item["clip"])),
            "prix_revele": item["prix"], "cta": item["cta"], "export": out,
            "nouveau_rendu": "sequence video + reveal prix"}


def main(n_choix=4, n_devine=4, seed=1):
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(seed)
    manifest = []
    for i, item in enumerate(build_choix(n_choix, rng), 1):
        out = os.path.join(OUT, f"choix_{i:02d}.mp4")
        sr.render_grid_2x2(item["tiles"], item["bg"], item["hook"], ACTIONS, out)
        manifest.append(manifest_choix(item, out))
        print(f"[choix {i}/{n_choix}] {item['hook']} | {item['models']}", flush=True)
    for i, item in enumerate(build_devine(n_devine, rng), 1):
        out = os.path.join(OUT, f"devine_{i:02d}.mp4")
        _render_devine(item, out)
        manifest.append(manifest_devine(item, out))
        print(f"[devine {i}/{n_devine}] {item['hook']} -> {item['prix']}", flush=True)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"OK — {n_choix + n_devine} reels + manifest dans {OUT}")


if __name__ == "__main__":
    main()
