"""Sous-système hooks : couche d'engagement orthogonale (≠ mécanique, ≠ layout).
Un fichier JSON par mécanique ; chaque entrée porte son `angle` (analytics)."""
import os, json, functools
from backend.silent import registry

_HOOKS_DIR = os.path.join(os.path.dirname(__file__), "hooks")


@functools.lru_cache(maxsize=None)
def load_hooks(mechanic):
    """Liste [{text, angle}] pour une mécanique. Fail-fast si fichier manquant (R2)."""
    m = registry.MECHANICS.get(mechanic)
    if m is None:
        raise ValueError(f"unknown mechanic: {mechanic!r}")
    path = os.path.join(_HOOKS_DIR, m["hook_file"])
    if not os.path.isfile(path):
        raise FileNotFoundError(f"hook file missing for {mechanic!r}: {path}")
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    if not entries:
        raise ValueError(f"empty hook file for {mechanic!r}")
    return entries


def pick_hook(mechanic, rng):
    """Tire (text, angle) au hasard (seedé via `rng`)."""
    e = rng.choice(load_hooks(mechanic))
    return e["text"], e["angle"]
