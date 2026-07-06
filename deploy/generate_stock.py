"""Générateur de STOCK vacances : pré-produit un mix de reels (5 formats 1A +
choix 4 montres + devine le prix) avec un PLANNING daté (jour x créneau) et un
manifest de postage. Objectif : tout rendre en local une fois, le serveur n'a
plus qu'à POSTER selon planning.json (léger). NE POSTE RIEN.
Sortie : output/stock/ (mp4 + planning.json)."""
import os
import sys
import json
import random
import datetime
import collections
import importlib.util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.silent import policy, render
from backend.silent.strategy import ContentStrategy
from backend.silent import special_render as sr
from backend.config import BASE_HASHTAGS

# CTA texte ajouté à la caption selon le type logué (engagement)
_CTA_TEXT = {"comment": "Dis-le en commentaire 👇", "question": "Réponds en commentaire 👇",
             "dm": "Écris « MONTRE » en DM"}


def _caption(hook, cta_type=None):
    """Caption robuste (sans Gemini) : hook + CTA + hashtags de base."""
    parts = [hook]
    if cta_type and _CTA_TEXT.get(cta_type):
        parts.append(_CTA_TEXT[cta_type])
    tags = " ".join(BASE_HASHTAGS)
    return "\n".join(parts) + "\n\n" + tags

# import du générateur de formats spéciaux (banques + builders)
_SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_special_formats.py")
_spec = importlib.util.spec_from_file_location("genspecial", _SP)
special = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(special)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "stock")   # dossier VERSIONNÉ (poussé sur GitHub pour Actions)
SLOTS = [(7, 0), (11, 30), (15, 0), (17, 0), (21, 0)]   # 5 reels/jour (cf scheduler)
PLATFORMS = ["instagram", "tiktok"]

FORMATS_1A = {"test", "revelation_psy", "trahison", "perception", "test_perso"}
# poids (mix guide + ~25% formats spéciaux)
WEIGHTS = {"test": 3.0, "revelation_psy": 2.5, "trahison": 2.0, "perception": 1.5,
           "test_perso": 1.0, "choix_4": 2.0, "devine_prix": 2.0}


def _weighted_no_repeat(prev, rng):
    items = [f for f in WEIGHTS if f != prev] or list(WEIGHTS)
    w = [WEIGHTS[f] for f in items]
    return rng.choices(items, weights=w, k=1)[0]


def _plan(days, start_date, rng):
    """Liste ordonnée d'items {date, heure, format} sans 2 fois le même format d'affilée."""
    plan, prev = [], None
    for d in range(days):
        day = start_date + datetime.timedelta(days=d)
        for (h, m) in SLOTS:
            fmt = _weighted_no_repeat(prev, rng)
            prev = fmt
            plan.append({"date": day.isoformat(), "heure": f"{h:02d}:{m:02d}", "format": fmt})
    return plan


def _decide_1a(fmt, recent_hooks, recent_trios, rng):
    """Recipe 1A avec anti-répétition glissante : évite un hook OU un trio déjà vus
    dans les 4 derniers reels du même format (re-tirage borné)."""
    r = None
    for _ in range(30):
        r = policy.decide(ContentStrategy(goal="engagement", mechanic=fmt, count=1),
                          history=[], seed=rng.randrange(1 << 30))
        trio = tuple(r.assets)
        if r.hook not in recent_hooks[fmt] and trio not in recent_trios[fmt]:
            recent_hooks[fmt].append(r.hook); recent_trios[fmt].append(trio)
            return r
    recent_hooks[fmt].append(r.hook); recent_trios[fmt].append(tuple(r.assets))
    return r


def _render_item(fmt, rng, out, choix_pool, devine_pool, recent_hooks, recent_trios):
    """Rend un reel selon son format. Retourne (hook, extra)."""
    if fmt in FORMATS_1A:
        r = _decide_1a(fmt, recent_hooks, recent_trios, rng)
        render.render_recipe(r, out)
        return r.hook, {"montres": [os.path.basename(os.path.dirname(a)) for a in r.assets],
                        "labels": [l[0] for l in (r.labels or [])], "cta": r.cta_type}
    if fmt == "choix_4":
        item = choix_pool.pop()
        sr.render_grid_2x2(item["tiles"], item["bg"], item["hook"], special.ACTIONS, out)
        return item["hook"], {"montres": item["models"], "actions": special.ACTIONS}
    if fmt == "devine_prix":
        item = devine_pool.pop()
        special._render_devine(item, out)
        return item["hook"], {"montre": os.path.basename(os.path.dirname(item["clip"])),
                              "prix": item["prix"], "cta": item["cta"]}
    raise ValueError(f"format inconnu: {fmt}")


def main(days=1, start=None, seed=1):
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(seed)
    start_date = (datetime.date.fromisoformat(start) if start
                  else datetime.date.today() + datetime.timedelta(days=1))
    plan = _plan(days, start_date, rng)
    # pools de formats spéciaux (anti-répétition interne : quatuors/montres uniques)
    n_choix = sum(1 for s in plan if s["format"] == "choix_4")
    n_devine = sum(1 for s in plan if s["format"] == "devine_prix")
    choix_pool = special.build_choix(n_choix, rng) if n_choix else []
    devine_pool = special.build_devine(n_devine, rng) if n_devine else []
    # anti-répétition glissante des reels 1A (fenêtre 4 par format)
    recent_hooks = {f: collections.deque(maxlen=4) for f in FORMATS_1A}
    recent_trios = {f: collections.deque(maxlen=4) for f in FORMATS_1A}
    planning = []
    for i, slot in enumerate(plan, 1):
        fmt = slot["format"]
        name = f"stock_{i:03d}_{fmt}.mp4"
        out = os.path.join(OUT, name)
        hook, extra = _render_item(fmt, rng, out, choix_pool, devine_pool,
                                   recent_hooks, recent_trios)
        planning.append({
            "id": i, "date": slot["date"], "heure": slot["heure"],
            "format": fmt, "hook": hook, "fichier": name,
            "caption": _caption(hook, extra.get("cta")),
            "platforms": PLATFORMS, "posted": False, **extra,
        })
        print(f"[{i:03d}] {slot['date']} {slot['heure']} | {fmt:14s} | {hook}", flush=True)
    with open(os.path.join(OUT, "planning.json"), "w", encoding="utf-8") as f:
        json.dump(planning, f, ensure_ascii=False, indent=2)
    print(f"OK — {len(planning)} reels ({days} j) + planning.json dans {OUT}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--start", type=str, default=None, help="YYYY-MM-DD (def: demain)")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    main(days=a.days, start=a.start, seed=a.seed)
