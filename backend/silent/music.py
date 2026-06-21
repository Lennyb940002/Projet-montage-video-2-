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


def pick_track(rng, music_dir=None):
    """Tire un morceau (seedé). None si aucun son dans le dossier."""
    tracks = list_tracks(music_dir)
    return rng.choice(tracks) if tracks else None
