"""Sous-système hooks : couche d'engagement orthogonale (≠ mécanique, ≠ layout).
Source prioritaire = DOSSIER_CONCEPTS.md (via concepts.py) ; fallback = banques
JSON intégrées (chaque entrée porte son `angle` pour l'analytics)."""
import os, json, functools
from backend.silent import registry
from backend.silent import concepts as _concepts

_HOOKS_DIR = os.path.join(os.path.dirname(__file__), "hooks")
_BANKS_DIR = os.path.join(os.path.dirname(__file__), "banks")   # banques contenu 1A


@functools.lru_cache(maxsize=None)
def load_hooks(mechanic):
    """Liste [{text, angle}] pour une mécanique. Cherche le hook_file d'abord
    dans banks/ (contenu 1A), puis dans hooks/ (legacy). Fail-fast sinon (R2)."""
    m = registry.MECHANICS.get(mechanic)
    if m is None:
        raise ValueError(f"unknown mechanic: {mechanic!r}")
    for d in (_BANKS_DIR, _HOOKS_DIR):
        path = os.path.join(d, m["hook_file"])
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                entries = json.load(f)
            if not entries:
                raise ValueError(f"empty hook file for {mechanic!r}")
            return entries
    raise FileNotFoundError(f"hook file missing for {mechanic!r}: {m['hook_file']}")


def pick_hook(mechanic, rng):
    """Tire (text, angle) au hasard (seedé via `rng`). Priorité au dossier
    concepts (édité par l'utilisateur) ; sinon banque JSON intégrée."""
    pool = _concepts.hooks_for(mechanic)
    if pool:
        return rng.choice(pool)
    e = rng.choice(load_hooks(mechanic))
    return e["text"], e["angle"]
