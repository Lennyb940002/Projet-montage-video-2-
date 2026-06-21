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


def model_of(path):
    """Le 'modèle' (= la montre) = nom du dossier parent du clip."""
    return os.path.basename(os.path.dirname(path))


def _by_model(pool):
    d = {}
    for p in pool:
        d.setdefault(model_of(p), []).append(p)
    return d


def sample(constraint, rng, clips_dir=None, exclude_models=()):
    """Tire `count` clips de `count` MODÈLES DISTINCTS (jamais 2 fois la même
    montre dans une vidéo). Évite en priorité les modèles `exclude_models`
    (montres des vidéos récentes) ; relâche si pas assez de modèles frais
    (best-effort, ne échoue jamais tant qu'il y a assez de modèles distincts)."""
    clips_dir = clips_dir or _DEFAULT
    count = constraint["count"]
    by_model = _by_model(_list_assets(clips_dir))
    models = list(by_model)
    if len(models) < count:
        raise ValueError(
            f"not enough distinct models in {clips_dir}: need {count}, have {len(models)}")
    ex = set(exclude_models or ())
    fresh = [m for m in models if m not in ex]
    stale = [m for m in models if m in ex]
    rng.shuffle(fresh); rng.shuffle(stale)
    chosen = (fresh + stale)[:count]      # frais d'abord, complète avec récents si besoin
    return [rng.choice(by_model[m]) for m in chosen]
