"""Sampler d'assets (Option C). Étape MÉCANIQUE : ne décide rien, réalise le
tirage demandé par les contraintes émises par le Policy. Seedé => reproductible.
V1 : filters ignorés (pas de tags) ; V2 les exploitera."""
import os
from backend.config import DEFAULT_CLIPS_DIR, SILENT

_EXTS = (".mp4", ".mov", ".webm", ".mkv")
# Banque par défaut du Silent Engine : la banque mannequins/montres (sinon legacy).
_DEFAULT = SILENT.get("clips_dir") or DEFAULT_CLIPS_DIR


def _list_assets(clips_dir):
    """Liste RÉCURSIVE des clips vidéo (la banque est organisée en sous-dossiers
    par modèle de montre). Images exclues : on veut des vidéos animées."""
    out = []
    for root, _dirs, files in os.walk(clips_dir):
        for name in files:
            if os.path.splitext(name)[1].lower() in _EXTS:
                out.append(os.path.join(root, name))
    return sorted(out)


def sample(constraint, rng, clips_dir=None):
    """Tire `constraint['count']` assets distincts depuis la banque (seedé).
    Lève ValueError si la banque n'a pas assez d'assets (R1/R2)."""
    clips_dir = clips_dir or _DEFAULT
    count = constraint["count"]
    pool = _list_assets(clips_dir)
    if len(pool) < count:
        raise ValueError(
            f"not enough clips in {clips_dir}: need {count}, found {len(pool)}")
    return rng.sample(pool, count)
