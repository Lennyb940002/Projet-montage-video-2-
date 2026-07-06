"""Pré-génère 5 jours de contenu (vidéos + carrousels + stories de partage +
stories promo) dans un dossier `content5/`, avec un `manifest.json` qui décrit
quoi poster à quel jour/créneau. Destiné à être poussé sur GitHub Actions pour
publier sans le PC pendant 5 jours.

Lancement :  PYTHONPATH=. python deploy/prepare_5days.py [start_date=YYYY-MM-DD] [n_days=5]
"""
import json
import os
import random
import shutil
import sys
import uuid

from backend.config import WORKDIR, SILENT, PHOTOS
from backend.silent import policy as _policy
from backend.silent.strategy import ContentStrategy
from backend.silent.render import render_recipe
from backend.distribution import caption_seo
from backend.posts import orchestrator as corch
from backend.posts.carousel import render_carousel, THEME_ORDER
from backend.posts import story as story_mod
from backend.posts import promo as promo_mod
from backend.posts import cta

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "content5")
OUT = os.path.abspath(OUT)

VIDEO_SLOTS = [("07:00", "engagement"), ("11:30", "engagement"),
               ("15:00", "engagement"), ("17:00", "engagement"),
               ("21:00", "retention")]
CAROUSEL_SLOTS = [("12:00", "value"), ("18:00", "objection")]
PROMO_SLOTS = ["09:00", "14:00", "20:00"]

FAMILY = {"test": "identité", "elimination": "élimination", "projection": "projection",
          "vote": "duel", "revelation": "révélation", "collection": "duel",
          "top3": "classement", "pov": "pov"}
PLATFORMS = ["instagram", "tiktok"]
STORY_HOOK = {"value": "📚 Nouveau conseil", "objection": "🔥 Nouveau contenu"}


def _model_names(recipe):
    models = SILENT.get("models") or {}
    out = []
    for a in recipe.assets:
        folder = os.path.basename(os.path.dirname(a))
        out.append((models.get(folder) or {}).get("name", folder))
    return out


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "2026-06-26"
    n_days = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)

    manifest = {"start_date": start, "n_days": n_days, "slots": []}
    rng = random.Random(42)

    # état anti-répétition vidéo
    history, recent_models = [], []
    # carrousels
    value_recent, obj_recent = [], []
    car_count = 0
    # promos : ordre entrelacé des 13 photos
    promo_photos = promo_mod.list_photos()
    promo_order = promo_mod.interleaved_order(promo_photos)
    promo_i = 0

    for day in range(n_days):
        # ---- VIDÉOS ----
        for hhmm, goal in VIDEO_SLOTS:
            strat = ContentStrategy(goal=goal, count=1)
            seed = rng.randrange(10 ** 9)
            recipe = _policy.decide(strat, history=list(history), seed=seed,
                                    exclude_models=tuple(recent_models[:2]))
            base = f"d{day}_{hhmm.replace(':', '')}_reel"
            mp4 = os.path.join(OUT, base + ".mp4")
            render_recipe(recipe, mp4)
            names = _model_names(recipe)
            caption, tags = caption_seo.build_caption(recipe.mechanic, names, recipe.hook)
            full = caption + ("\n\n" + " ".join(tags) if tags else "")
            history.insert(0, {"mechanic": recipe.mechanic,
                               "content_angle": recipe.content_angle, "layout": recipe.layout})
            folders = [os.path.basename(os.path.dirname(a)) for a in recipe.assets]
            recent_models = folders + recent_models
            manifest["slots"].append({
                "day": day, "time": hhmm, "type": "reel", "file": base + ".mp4",
                "caption": full, "platforms": PLATFORMS,
                "family": FAMILY.get(recipe.mechanic, recipe.mechanic),
                "hook": recipe.hook, "models": " + ".join(names)})
            print(f"[d{day} {hhmm}] reel {recipe.mechanic} ({recipe.hook[:30]})", flush=True)

        # ---- CARROUSELS (+ story de partage) ----
        for hhmm, kind in CAROUSEL_SLOTS:
            bank = corch.load_bank(kind)
            recent = value_recent if kind == "value" else obj_recent
            entry = corch.pick_script(bank, recent, rng)
            recent.insert(0, entry["topic"])
            theme = THEME_ORDER[car_count % len(THEME_ORDER)]
            car_count += 1
            code = cta.next_code()
            content = dict(entry["content"])
            content["outro_cta"] = f"DM « {code} » pour voir les modèles"
            caption = entry["caption"].rstrip() + f"\n\n📩 Écris « {code} » en DM et je te réponds direct."
            prefix = f"d{day}_{hhmm.replace(':', '')}_c"
            paths = render_carousel(content, theme=theme, out_dir=OUT, prefix=prefix)
            files = [os.path.basename(p) for p in paths]
            story_png = os.path.join(OUT, f"d{day}_{hhmm.replace(':', '')}_story.png")
            story_mod.render_story(paths[0], story_png, hook=STORY_HOOK[kind], cta=f"📩 DM « {code} »")
            manifest["slots"].append({
                "day": day, "time": hhmm, "type": "carousel", "files": files,
                "caption": caption, "platforms": PLATFORMS,
                "story": os.path.basename(story_png), "cta_code": code,
                "family": "carrousel", "topic": entry["topic"]})
            print(f"[d{day} {hhmm}] carrousel {kind} {entry['id']} ({theme})", flush=True)

        # ---- STORIES PROMO ----
        for hhmm in PROMO_SLOTS:
            name = promo_order[promo_i % len(promo_order)]
            promo_i += 1
            src = os.path.join(PHOTOS["dir"], name)
            outp = os.path.join(OUT, f"d{day}_{hhmm.replace(':', '')}_promo.png")
            story_mod.render_promo_story(outp, src)
            manifest["slots"].append({
                "day": day, "time": hhmm, "type": "story_promo",
                "file": os.path.basename(outp), "platforms": ["instagram"],
                "family": "photo", "model": promo_mod._model(name)})
            print(f"[d{day} {hhmm}] promo {promo_mod._model(name)}", flush=True)

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"\nOK — {len(manifest['slots'])} posts générés dans {OUT}")


if __name__ == "__main__":
    main()
