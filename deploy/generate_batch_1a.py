"""Génère le lot de test 1A (30 reels) en revue manuelle. NE POSTE RIEN.
Anti-répétition en mémoire sur le lot (hooks <=2/méca, trios uniques, famille
voyante pas toujours en n°2, CTA en rotation). Manifest JSON d'audit."""
import os
import sys
import json
import random
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.silent import policy, content
from backend.silent.strategy import ContentStrategy
from backend.silent import render as _render

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "output", "batch_1a")
DISTRIB = [("test", 10), ("revelation_psy", 8), ("trahison", 6),
           ("perception", 4), ("test_perso", 2)]
_VOYANTES = {"or_rose", "ruby"}   # familles voyantes : pas toujours en position 2


def build_plan():
    return [{"mechanic": m} for m, n in DISTRIB for _ in range(n)]


def _reorder_no_flashy_center(recipe, rng):
    """Évite qu'une famille voyante soit toujours en n°2 (index central).
    Réordonne assets ET labels ensemble pour garder la cohérence montre↔label."""
    fams = [content.detect_family(a) for a in recipe.assets]
    if len(recipe.assets) == 3 and fams[1] in _VOYANTES and rng.random() < 0.7:
        order = [0, 2, 1]
        assets = tuple(recipe.assets[i] for i in order)
        labels = tuple(recipe.labels[i] for i in order) if recipe.labels else None
        return replace(recipe, assets=assets, labels=labels)
    return recipe


def build_recipes(seed=0):
    rng = random.Random(seed)
    recipes = []
    used_hooks = {}          # mechanic -> {hook: count}
    used_trios = set()
    for item in build_plan():
        mech = item["mechanic"]
        r = None
        for _ in range(40):  # ré-essais bornés jusqu'à respecter l'anti-répétition
            s = rng.randrange(1 << 30)
            cand = policy.decide(ContentStrategy(goal="engagement", mechanic=mech, count=1),
                                 history=[], seed=s)
            cand = _reorder_no_flashy_center(cand, rng)
            hc = used_hooks.setdefault(mech, {})
            trio = tuple(cand.assets)
            if hc.get(cand.hook, 0) >= 2 or trio in used_trios:
                r = cand
                continue
            hc[cand.hook] = hc.get(cand.hook, 0) + 1
            used_trios.add(trio)
            r = cand
            break
        recipes.append(r)
    return recipes


def manifest_entry(recipe, out_path):
    familles = [content.detect_family(a) for a in recipe.assets]
    labels = list(recipe.labels or [])
    # mode déduit du label RÉELLEMENT rendu (fiable pour l'audit), pas d'un re-tirage
    modes = [content.label_mode_of(recipe.mechanic, fam, lbl[0])
             for fam, lbl in zip(familles, labels)]
    return {
        "mecanique": recipe.mechanic,
        "hook": recipe.hook,
        "montres": list(recipe.assets),
        "familles_detectees": familles,
        "labels": [list(l) for l in labels],
        "cta": recipe.cta_type,
        "mode_coherence": modes,
        "chemin_export": out_path,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    recipes = build_recipes(seed=1)
    manifest = []
    for i, r in enumerate(recipes, 1):
        out = os.path.join(OUT_DIR, f"reel_{i:02d}_{r.mechanic}.mp4")
        _render.render_recipe(r, out)
        manifest.append(manifest_entry(r, out))
        print(f"[{i:02d}/30] {r.mechanic} -> {os.path.basename(out)}", flush=True)
    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"OK — {len(recipes)} reels + manifest dans {OUT_DIR}")


if __name__ == "__main__":
    main()
