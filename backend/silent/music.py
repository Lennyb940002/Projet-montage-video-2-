"""Banque musicale du Silent Engine : pioche un morceau pour le bed audio.
L'utilisateur dépose ses sons dans SILENT['music_dir'] (n'importe quel mp3/wav).
Aucun son n'est sourcé automatiquement — c'est l'utilisateur qui remplit le
dossier avec les sons qu'il veut (tendance ou non, à sa discrétion)."""
import os
from backend.config import SILENT

_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")


def list_tracks(music_dir=None):
    """Liste RÉCURSIVE des sons (la banque peut avoir des sous-dossiers,
    ex 'TikTok 10s')."""
    d = music_dir or SILENT.get("music_dir")
    if not d or not os.path.isdir(d):
        return []
    out = []
    for root, _dirs, files in os.walk(d):
        for name in files:
            if os.path.splitext(name)[1].lower() in _EXTS:
                out.append(os.path.join(root, name))
    return sorted(out)


def pick_track(rng, music_dir=None, exclude=()):
    """Tire un morceau (seedé), en évitant ceux de `exclude` (sons récents).
    Si tout est exclu, on recycle (le pool complet). None si dossier vide."""
    tracks = list_tracks(music_dir)
    if not tracks:
        return None
    ex = set(exclude or ())
    fresh = [t for t in tracks if t not in ex]
    return rng.choice(fresh if fresh else tracks)
