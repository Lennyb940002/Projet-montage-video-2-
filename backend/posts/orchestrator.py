"""Orchestrateur carrousels valeur/objection : pioche un script (anti-répétition),
coloris en rotation, rend, publie IG+TikTok, puis enchaîne la story de partage.
Auto-direct (PAS de validation Telegram pour les carrousels). Non bloquant."""
import json
import os
import random
import uuid

from backend.config import WORKDIR, POSTS_DB
from backend import settings
from backend.distribution import uploadpost
from backend.posts.carousel import render_carousel, THEME_ORDER
from backend.posts import story as story_mod
from backend.posts import cta
from backend.posts.store import PostsStore

# Banque par type de créneau.
BANKS = {"value": "scripts_value.json", "objection": "scripts_conversion.json"}
# Accroche story selon le type.
STORY_HOOK = {"value": "📚 Nouveau conseil", "objection": "🔥 Nouveau contenu"}
TOPIC_CYCLE = 7   # un sujet ne revient pas avant 7 posts


def _bank_path(kind):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), BANKS[kind])


def load_bank(kind):
    with open(_bank_path(kind), encoding="utf-8") as f:
        return json.load(f)


def pick_script(bank, recent_topics, rng=random):
    """Choisit un script dont le sujet n'a pas servi récemment (sinon recycle)."""
    recent = set(recent_topics or [])
    fresh = [e for e in bank if e["topic"] not in recent]
    return rng.choice(fresh or bank)


def _cleanup(out_dir):
    try:
        for f in os.listdir(out_dir):
            os.remove(os.path.join(out_dir, f))
        os.rmdir(out_dir)
    except OSError:
        pass


def generate_and_post(kind, store=None, out_dir=None, dry_run=False, with_story=True):
    """Produit + publie un carrousel pour le créneau `kind` ('value'|'objection').
    `dry_run` : rend seulement (aucune publication). Renvoie un dict de résultat."""
    if kind not in BANKS:
        raise ValueError(f"kind inconnu: {kind!r}")
    store = store or PostsStore(POSTS_DB)
    s = settings.load()
    user, token = s.get("uploadpost_user", ""), s.get("uploadpost_token", "")
    platforms = s.get("uploadpost_platforms") or ["instagram", "tiktok"]

    bank = load_bank(kind)
    entry = pick_script(bank, store.recent_topics(TOPIC_CYCLE))
    count = store.count()
    theme = THEME_ORDER[count % len(THEME_ORDER)]

    # Code CTA unique -> attribution des DM (injecté CTA + caption + story).
    code = cta.next_code()
    content = dict(entry["content"])
    content["outro_cta"] = f"DM « {code} » pour voir les modèles"
    caption = entry["caption"].rstrip() + f"\n\n📩 Écris « {code} » en DM et je te réponds direct."

    out_dir = out_dir or os.path.join(WORKDIR, "post_" + uuid.uuid4().hex)
    paths = render_carousel(content, theme=theme, out_dir=out_dir, prefix="c")

    result = {"kind": kind, "id": entry["id"], "topic": entry["topic"],
              "theme": theme, "cta_code": code}
    if dry_run:
        result.update(paths=paths, dry_run=True)
        return result

    # 1) carrousel feed -> IG (+ TikTok)
    res = uploadpost.post_photos(paths, caption, platforms, user, token)
    posted = bool(res.get("ok"))

    # 2) story de partage (image, IG) — même code CTA
    story_res = None
    if with_story and posted:
        story_png = os.path.join(out_dir, "story.png")
        story_mod.render_story(paths[0], story_png,
                               hook=STORY_HOOK.get(kind), cta=f"📩 DM « {code} »")
        story_res = uploadpost.post_photos([story_png], "", ["instagram"], user, token,
                                           media_type="STORIES")

    pid = store.insert(entry["topic"], theme, caption=caption,
                       n_slides=len(paths), status="posted" if posted else "failed")
    _cleanup(out_dir)
    result.update(pid=pid, posted=posted, carousel=res, story=story_res)
    return result
