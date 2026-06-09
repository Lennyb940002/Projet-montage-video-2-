"""Banque musicale.

Phase 1 (Task 0) : validation non-bloquante de la bibliothèque.
Phase 2 (Task 3) : choix déterministe + cache LUFS/durée par fichier.

Règle produit : ce module ne lève jamais d'exception sur une bibliothèque
incomplète. Il décrit l'état et le code aval décide quoi faire.
"""
import json
import os
import random as _random

from backend import ffmpeg
from backend.pipeline.audio_meta import lufs_of

CATEGORIES = ("Luxury", "Hype")
SUPPORTED = (".mp3", ".wav", ".flac")
MIN_TRACKS_PER_CATEGORY = 3
INDEX_NAME = ".music_index.json"


def list_tracks(category, root):
    """Liste triée des tracks d'une catégorie. Ignore fichiers cachés et formats
    non supportés. Renvoie [] si la catégorie n'existe pas."""
    d = os.path.join(root, category)
    if not os.path.isdir(d):
        return []
    out = []
    for f in os.listdir(d):
        if f.startswith("."):
            continue
        if os.path.splitext(f)[1].lower() not in SUPPORTED:
            continue
        out.append(os.path.join(d, f))
    return sorted(out)


def validate_library(root):
    """Rapport non-bloquant sur l'état de la bibliothèque.

    Renvoie :
      {
        "ok": bool,
        "missing_categories": [str, ...],
        "tracks_found": {"Luxury": int, "Hype": int},
        "min_required_per_category": int
      }
    """
    found = {c: len(list_tracks(c, root)) for c in CATEGORIES}
    missing = [c for c, n in found.items() if n < MIN_TRACKS_PER_CATEGORY]
    return {
        "ok": len(missing) == 0,
        "missing_categories": missing,
        "tracks_found": found,
        "min_required_per_category": MIN_TRACKS_PER_CATEGORY,
    }


# --- Cache LUFS / durée (par catégorie) -------------------------------------

def _index_path(root):
    return os.path.join(root, INDEX_NAME)


def _load_index(root):
    p = _index_path(root)
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_index(root, idx):
    try:
        with open(_index_path(root), "w", encoding="utf-8") as f:
            json.dump(idx, f, indent=2)
    except OSError:
        pass


def index_category(category, root):
    """Indexe les tracks d'une catégorie : (LUFS, durée, mtime) par fichier.
    Cache JSON dans `<root>/.music_index.json`. Re-scan UNIQUEMENT les fichiers
    nouveaux ou modifiés (mtime).
    """
    full = _load_index(root)
    cat_idx = full.get(category, {})
    new_cat = {}
    for f in list_tracks(category, root):
        mtime = os.path.getmtime(f)
        cached = cat_idx.get(f)
        if cached and cached.get("mtime") == mtime:
            new_cat[f] = cached     # cache hit
        else:
            new_cat[f] = {           # cache miss -> mesure
                "mtime": mtime,
                "lufs": lufs_of(f),
                "dur": ffmpeg.probe_duration(f),
            }
    full[category] = new_cat
    _save_index(root, full)
    return new_cat


# --- Choix déterministe ------------------------------------------------------

def choose(category, target_dur, root, rng=None):
    """Choisit une track d'une catégorie.

    Garde-fou anti-boucle : SEULES les tracks dont la durée >= target_dur + 5s
    sont éligibles. Aucune piste éligible -> renvoie None (le code aval doit
    gérer ce cas : warning "no_track_long_enough", plan["music"]=None).

    - Déterministe si `rng` est un `random.Random` fourni.
    - Renvoie None si la catégorie est vide ou si aucune track n'est éligible.
    """
    idx = index_category(category, root)
    if not idx:
        return None
    eligible = [f for f, e in idx.items() if e.get("dur", 0) >= target_dur + 5.0]
    if not eligible:
        return None    # garde-fou : refuse la boucle implicite
    rng = rng or _random.Random()
    return rng.choice(sorted(eligible))
