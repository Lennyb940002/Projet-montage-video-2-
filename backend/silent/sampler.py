"""Sampler d'assets (Option C). Étape MÉCANIQUE : ne décide rien, réalise le
tirage demandé par les contraintes émises par le Policy. Seedé => reproductible.
V1 : filters ignorés (pas de tags) ; V2 les exploitera."""
import os, glob
from backend.config import DEFAULT_CLIPS_DIR

_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".png", ".jpg", ".jpeg", ".webp")


def _list_assets(clips_dir):
    out = []
    for p in sorted(glob.glob(os.path.join(clips_dir, "*"))):
        if os.path.splitext(p)[1].lower() in _EXTS:
            out.append(p)
    return out


def sample(constraint, rng, clips_dir=DEFAULT_CLIPS_DIR):
    """Tire `constraint['count']` assets distincts depuis la banque (seedé).
    Lève ValueError si la banque n'a pas assez d'assets (R1/R2)."""
    count = constraint["count"]
    pool = _list_assets(clips_dir)
    if len(pool) < count:
        raise ValueError(
            f"not enough clips in {clips_dir}: need {count}, found {len(pool)}")
    return rng.sample(pool, count)
