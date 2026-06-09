"""Banque musicale.

Phase 1 (Task 0) : validation non-bloquante de la bibliothèque.
Phase 2 (Task 3) : choix déterministe + cache LUFS/durée.

Règle produit : ce module ne lève jamais d'exception sur une bibliothèque
incomplète. Il décrit l'état et le code aval décide quoi faire.
"""
import os

CATEGORIES = ("Luxury", "Hype")
SUPPORTED = (".mp3", ".wav", ".flac")
MIN_TRACKS_PER_CATEGORY = 3


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
