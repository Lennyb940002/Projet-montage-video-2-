"""Stories PROMO d'été à partir des photos réelles : 3/jour, bien espacées.
Cycle TOUTES les 13 photos avant d'en répéter une, et jamais 2 fois le même
modèle d'affilée (ordre entrelacé glouton). Story IG (média éphémère 24h)."""
import json
import os
import re
import uuid
from collections import defaultdict

from backend import settings
from backend.config import PHOTOS, WORKDIR
from backend.distribution import uploadpost
from backend.posts.story import render_promo_story

STATE_PATH = os.path.join(os.path.expanduser("~"), ".automontage", "promo_state.json")
OLD_PRICE, NEW_PRICE = "194,50", "179 euros"
_EXT = (".jpeg", ".jpg", ".png")


def _model(filename):
    return re.sub(r"_\d+$", "", os.path.splitext(filename)[0])


def list_photos():
    d = PHOTOS["dir"]
    return sorted(f for f in os.listdir(d) if f.lower().endswith(_EXT))


def interleaved_order(photos):
    """Ordre entrelacé : jamais 2 fois le même modèle d'affilée (glouton :
    on place à chaque pas le modèle le plus nombreux restant ≠ précédent)."""
    groups = defaultdict(list)
    for p in photos:
        groups[_model(p)].append(p)
    remaining = {m: list(v) for m, v in groups.items()}
    order, last = [], None
    for _ in range(sum(len(v) for v in remaining.values())):
        cand = sorted((m for m in remaining if remaining[m]), key=lambda m: -len(remaining[m]))
        pick = next((m for m in cand if m != last), cand[0])
        order.append(remaining[pick].pop(0))
        last = pick
    return order


def _load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(st):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def next_photo():
    """Renvoie le prochain fichier photo (cycle entrelacé, persistant)."""
    photos = list_photos()
    st = _load_state()
    order = st.get("order")
    if not order or sorted(order) != sorted(photos):   # (re)construit si banque changée
        order = interleaved_order(photos)
        st["order"], st["i"] = order, 0
    i = st.get("i", 0) % len(order)
    st["i"] = (i + 1) % len(order)
    _save_state(st)
    return order[i]


def post_promo(dry_run=False):
    """Rend + poste UNE story promo (prochain modèle du cycle). Renvoie un dict."""
    name = next_photo()
    photo = os.path.join(PHOTOS["dir"], name)
    out = os.path.join(WORKDIR, "promo_" + uuid.uuid4().hex + ".png")
    render_promo_story(out, photo, OLD_PRICE, NEW_PRICE)
    res = {"photo": name, "model": _model(name)}
    if dry_run:
        res["dry_run"] = True
        try:
            os.remove(out)
        except OSError:
            pass
        return res
    s = settings.load()
    r = uploadpost.post_photos([out], "", ["instagram"],
                               s.get("uploadpost_user", ""), s.get("uploadpost_token", ""),
                               media_type="STORIES")
    try:
        os.remove(out)
    except OSError:
        pass
    # marque la story promo comme famille 'photo' (pas 'carrousel') dans l'analytics
    try:
        from backend.posts import analytics
        analytics.flag_photo_recent(8)
    except Exception:
        pass
    res["posted"] = bool(r.get("ok"))
    return res
