"""Génère le STOCK COMPLET vacances (au-delà des reels) : stories question,
carrousels valeur + objection, stories promo, stories de partage — avec planning
daté unifié. Fusionne avec les reels déjà présents dans stock/planning.json.
Rendus : carousel.py / story.py (Playwright) + story_question.py (PIL).
NE POSTE RIEN. `--sample DATE` = génère 1 jour d'extras dans un dossier test."""
import os
import sys
import json
import random
import argparse
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.posts import carousel, story, promo, orchestrator, story_question
from backend.config import BASE_HASHTAGS, PHOTOS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK = os.path.join(ROOT, "stock")
PLANNING = os.path.join(STOCK, "planning.json")
TAGS = " ".join(BASE_HASHTAGS)
STORY_PLATFORMS = ["instagram", "facebook"]        # stories : pas TikTok
CARR_PLATFORMS = ["instagram", "facebook"]         # carrousels photo : IG+FB

# créneaux extras/jour : (heure, type)
EXTRAS = [("09:00", "promo"), ("12:00", "carrousel_valeur"), ("12:30", "partage"),
          ("13:00", "question"), ("14:00", "promo"), ("18:00", "carrousel_objection"),
          ("18:30", "partage"), ("20:00", "promo")]


def _gen_carrousel(kind_bank, date, heure, out_dir, theme, recent, rng, idx):
    bank = orchestrator.load_bank(kind_bank)
    entry = orchestrator.pick_script(bank, recent, rng)
    recent.append(entry["topic"])
    prefix = f"c_{date}_{heure.replace(':', '')}"
    paths = carousel.render_carousel(entry["content"], theme=theme, out_dir=out_dir, prefix=prefix)
    caption = entry["caption"].rstrip() + "\n\n📩 Écris « MONTRE » en DM."
    return {"kind": "carrousel", "type": kind_bank, "date": date, "heure": heure,
            "fichiers": [os.path.basename(p) for p in paths], "caption": caption,
            "platforms": CARR_PLATFORMS, "topic": entry["topic"], "posted": False,
            "_slides_abs": paths}


def _gen_question(date, heure, out_dir, n):
    q = story_question.QUESTIONS[n % len(story_question.QUESTIONS)]
    fn = f"story_q_{date}_{heure.replace(':', '')}.png"
    story_question.render_story_question(q, os.path.join(out_dir, fn))
    return {"kind": "story", "type": "question", "date": date, "heure": heure,
            "fichier": fn, "media_type": "STORIES", "caption": q,
            "platforms": STORY_PLATFORMS, "posted": False}


def _gen_promo(date, heure, out_dir):
    photo = promo.next_photo()
    if not os.path.isabs(photo) and not os.path.isfile(photo):
        photo = os.path.join(PHOTOS["dir"], photo)
    fn = f"story_promo_{date}_{heure.replace(':', '')}.png"
    story.render_promo_story(os.path.join(out_dir, fn), photo)
    return {"kind": "story", "type": "promo", "date": date, "heure": heure,
            "fichier": fn, "media_type": "STORIES",
            "caption": "Dispo maintenant — écris « MONTRE » en DM.",
            "platforms": STORY_PLATFORMS, "posted": False}


def _gen_partage(date, heure, out_dir, slide_abs, n):
    fn = f"story_partage_{date}_{heure.replace(':', '')}.png"
    story.render_story(slide_abs, os.path.join(out_dir, fn), n=n)
    return {"kind": "story", "type": "partage", "date": date, "heure": heure,
            "fichier": fn, "media_type": "STORIES",
            "caption": "Nouveau post 👇 va voir en profil.",
            "platforms": STORY_PLATFORMS, "posted": False}


def generate_extras_for_date(date, out_dir, state, rng):
    """Génère tous les extras d'une journée. Retourne les entrées planning."""
    os.makedirs(out_dir, exist_ok=True)
    entries, last_slide = [], None
    for heure, typ in EXTRAS:
        if typ == "promo":
            entries.append(_gen_promo(date, heure, out_dir))
        elif typ == "question":
            entries.append(_gen_question(date, heure, out_dir, state["qn"])); state["qn"] += 1
        elif typ == "carrousel_valeur":
            theme = ["dark", "light"][state["cn"] % 2]; state["cn"] += 1
            e = _gen_carrousel("value", date, heure, out_dir, theme, state["rv"], rng, state["cn"])
            last_slide = e.pop("_slides_abs")[0]; entries.append(e)
        elif typ == "carrousel_objection":
            theme = ["dark", "light"][state["cn"] % 2]; state["cn"] += 1
            e = _gen_carrousel("objection", date, heure, out_dir, theme, state["ro"], rng, state["cn"])
            last_slide = e.pop("_slides_abs")[0]; entries.append(e)
        elif typ == "partage":
            src = last_slide or os.path.join(out_dir, entries[-1].get("fichier", ""))
            entries.append(_gen_partage(date, heure, out_dir, src, state["pn"])); state["pn"] += 1
    return entries


def _reel_dates():
    plan = json.load(open(PLANNING, encoding="utf-8"))
    return sorted({it["date"] for it in plan}), plan


def main_full():
    dates, reels = _reel_dates()
    # normalise les reels au format unifié
    for it in reels:
        it.setdefault("kind", "video")
    state = {"qn": 0, "cn": 0, "pn": 0, "rv": [], "ro": []}
    rng = random.Random(7)
    extras = []
    for i, d in enumerate(dates, 1):
        print(f"[{i}/{len(dates)}] extras du {d}…", flush=True)
        extras += generate_extras_for_date(d, STOCK, state, rng)
    allp = reels + extras
    allp.sort(key=lambda it: (it["date"], it["heure"]))
    for i, it in enumerate(allp, 1):
        it["id"] = i
    json.dump(allp, open(PLANNING, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"OK — planning unifié : {len(reels)} reels + {len(extras)} extras = {len(allp)} posts")


def main_sample(date):
    out = os.path.join(ROOT, "output", "sample_day")
    os.makedirs(out, exist_ok=True)
    state = {"qn": 0, "cn": 0, "pn": 0, "rv": [], "ro": []}
    entries = generate_extras_for_date(date, out, state, random.Random(7))
    json.dump(entries, open(os.path.join(out, "sample_planning.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"ÉCHANTILLON {date} : {len(entries)} extras dans {out}")
    for e in entries:
        print(f"  {e['heure']} {e['kind']:9s} {e.get('type',''):18s} "
              f"{len(e.get('fichiers', [e.get('fichier')]))} img")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=str, help="génère 1 jour d'extras (YYYY-MM-DD) en test")
    a = ap.parse_args()
    if a.sample:
        main_sample(a.sample)
    else:
        main_full()
