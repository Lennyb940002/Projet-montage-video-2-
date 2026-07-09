# -*- coding: utf-8 -*-
"""Registre anti-répétition (daté) : garantit qu'on ne réutilise jamais le même
hook + le même son + la même photo d'intro. Journalise chaque choix dans
rafale_usage.json avec la date. Quand un pool est épuisé, reprend le moins
récemment utilisé (pour continuer sans jamais bloquer)."""
import os, json, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
USAGE_FILE = os.path.join(_HERE, "rafale_usage.json")

# --- Pools --------------------------------------------------------------------
# Hooks : liste (id, [(texte, couleur white|yellow), ...]). 'part 1' ajouté auto.
def _h(*chunks):
    return list(chunks) + [("part 1", "white")]

HOOK_POOL = [
    ("incroyables", _h(("Les", "white"), ("montres", "white"), ("incroyables", "yellow"),
                       ("que presque", "white"), ("personne", "white"), ("ne connaît", "yellow"))),
    ("sous-cotees", _h(("Les", "white"), ("montres", "white"), ("sous-cotées", "yellow"),
                       ("qui font", "white"), ("vraiment", "white"), ("la diff", "yellow"))),
    ("meilleures-ete", _h(("Les", "white"), ("meilleures", "yellow"), ("montres", "white"),
                          ("à avoir", "white"), ("absolument", "yellow"), ("cet été", "yellow"))),
    ("chrome-rares", _h(("Les", "white"), ("modèles", "white"), ("chrome", "yellow"),
                        ("que tu ne", "white"), ("vois pas", "white"), ("partout", "yellow"))),
    ("rotation", _h(("Les", "white"), ("montres", "white"), ("à ajouter", "yellow"),
                    ("à ta", "white"), ("rotation", "yellow"))),
    ("luxe-budget", _h(("Les", "white"), ("montres", "white"), ("qui font luxe", "yellow"),
                       ("sans exploser", "white"), ("ton budget", "yellow"))),
    ("discretes", _h(("Les", "white"), ("montres", "white"), ("discrètes", "yellow"),
                     ("mais", "white"), ("dangereuses", "yellow"))),
    ("avant-tlm", _h(("Les", "white"), ("modèles", "white"), ("à prendre", "yellow"),
                     ("avant que", "white"), ("tout le monde", "white"), ("les voie", "yellow"))),
    ("poignet-outfit", _h(("Les", "white"), ("pièces", "white"), ("au poignet", "yellow"),
                          ("qui changent", "white"), ("un outfit", "yellow"))),
    ("pas-cheap", _h(("Les", "white"), ("montres", "white"), ("accessibles", "yellow"),
                     ("qui ne font", "white"), ("pas cheap", "yellow"))),
    ("a-connaitre", _h(("Les", "white"), ("montres", "white"), ("à connaître", "yellow"),
                       ("avant", "white"), ("les autres", "yellow"))),
    ("nulle-part", _h(("Les", "white"), ("montres", "white"), ("qu'on voit", "yellow"),
                      ("nulle part", "white"), ("ailleurs", "yellow"))),
    ("changent-tout", _h(("Les", "white"), ("pièces", "white"), ("qui changent", "yellow"),
                         ("tout", "white"), ("au poignet", "yellow"))),
    ("niche", _h(("Les", "white"), ("montres", "white"), ("de niche", "yellow"),
                 ("qui font", "white"), ("la diff", "yellow"))),
    ("full-black", _h(("Les", "white"), ("montres", "white"), ("full black", "yellow"),
                      ("pour ta", "white"), ("rotation", "yellow"))),
    ("argentees", _h(("Les", "white"), ("montres", "white"), ("argentées", "yellow"),
                     ("qui passent", "white"), ("avec tout", "yellow"))),
    ("bleues", _h(("Les", "white"), ("montres", "white"), ("bleues", "yellow"),
                  ("les plus", "white"), ("propres", "yellow"))),
    ("or-rose", _h(("Les", "white"), ("montres", "white"), ("or rose", "yellow"),
                   ("qui font", "white"), ("la diff", "yellow"))),
    ("presence", _h(("Les", "white"), ("montres", "white"), ("avec une", "white"),
                    ("vraie", "white"), ("présence", "yellow"))),
    ("collection", _h(("Les", "white"), ("pièces", "white"), ("de collection", "yellow"),
                      ("à moins", "white"), ("de 200€", "yellow"))),
]
HOOKS = {hid: chunks for hid, chunks in HOOK_POOL}
HOOK_ORDER = [hid for hid, _ in HOOK_POOL]

SOUND_ORDER = ["21", "11", "39", "05", "01", "07", "20"]        # clés _assets/music
INTRO_ORDER = [f"intro_{i:02d}.jpg" for i in range(1, 21)]      # 20 photos


def load():
    try:
        return json.load(open(USAGE_FILE, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"used": []}


def save(u):
    json.dump(u, open(USAGE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _pick(pool, used_in_order):
    """1er non-utilisé ; sinon le moins récemment utilisé."""
    unused = [x for x in pool if x not in used_in_order]
    if unused:
        return unused[0]
    last = {v: i for i, v in enumerate(used_in_order)}   # index élevé = récent
    return min(pool, key=lambda x: last.get(x, -1))


def pick(u):
    """Retourne (hook_id, sound_key, intro_file) jamais combinés, met à jour u en
    mémoire (appeler save(u) à la fin). Chaque dimension évite ses propres répétitions."""
    used = u["used"]
    hk = _pick(HOOK_ORDER, [e["hook"] for e in used])
    sd = _pick(SOUND_ORDER, [e["sound"] for e in used])
    it = _pick(INTRO_ORDER, [e["intro"] for e in used])
    used.append({"date": datetime.date.today().isoformat(),
                 "hook": hk, "sound": sd, "intro": it})
    return hk, sd, it
