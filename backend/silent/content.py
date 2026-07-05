"""Couche contenu des reels (guide 2026-07-05). Banques JSON = source unique.
Décide labels (mix 80/20 crédible cohérent/surprise) et CTA. Aucun rendu ici."""
import os
import json
import functools

from backend.silent import registry

_BANKS = os.path.join(os.path.dirname(__file__), "banks")
_SURPRISE_RATE = 0.20
# palette ASS des cartouches (jamais de blanc -> lisible sur fond clair)
_PALETTE = ("&H0000FFFF&", "&H0000FF00&", "&H009314FF&", "&H00DC503C&")


@functools.lru_cache(maxsize=None)
def _bank(name):
    with open(os.path.join(_BANKS, name), encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def _familles():
    return _bank("familles.json")


def detect_family(asset_path):
    """Nom de famille d'après le dossier parent de l'asset ; None si inconnu."""
    folder = os.path.basename(os.path.dirname(asset_path))
    for name, f in _familles().items():
        if folder in f["dossiers"]:
            return name
    return None


def _label_mode(mechanic):
    return registry.MECHANICS[mechanic].get("label_mode", "profile")


def pick_labels(mechanic, assets, rng):
    """(labels, meta) : labels = ((texte, couleurASS), ...) 1 par montre ;
    meta = ({"famille":..., "mode":"coherent|surprise"}, ...). Mix 80/20 crédible :
    80% tirage dans `coherents`, 20% dans `surprise_acceptes` (jamais interdits)."""
    mode = _label_mode(mechanic)
    fam = _familles()
    labels, meta = [], []
    for i, asset in enumerate(assets):
        family = detect_family(asset)
        block = fam.get(family, {}).get("labels", {}).get(mode) if family else None
        if not block:                              # famille inconnue -> cohérent générique
            labels.append(("montre", _PALETTE[i % len(_PALETTE)]))
            meta.append({"famille": family, "mode": "coherent"})
            continue
        surprise = rng.random() < _SURPRISE_RATE and bool(block["surprise_acceptes"])
        pool = block["surprise_acceptes"] if surprise else block["coherents"]
        txt = rng.choice(pool)
        labels.append((txt, _PALETTE[i % len(_PALETTE)]))
        meta.append({"famille": family, "mode": "surprise" if surprise else "coherent"})
    return tuple(labels), tuple(meta)


def pick_cta(mechanic, rng, used_types=()):
    """(texte, type) d'un CTA. Évite en priorité les `used_types` récents
    (rotation comment/dm/question)."""
    cta = _bank("cta.json")
    fresh = [c for c in cta if c["type"] not in set(used_types)] or cta
    c = rng.choice(fresh)
    return c["text"], c["type"]
