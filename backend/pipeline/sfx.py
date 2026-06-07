import os, glob, random
from backend.config import SFX_DIR

EXTS = ("wav", "mp3", "flac")

def list_sfx(sfx_dir=SFX_DIR):
    """Tous les fichiers audio, récursivement (sous-dossiers inclus)."""
    if not os.path.isdir(sfx_dir):
        return []
    files = []
    for e in EXTS:
        files += glob.glob(os.path.join(sfx_dir, "**", f"*.{e}"), recursive=True)
    return sorted(files)

def pick(category, sfx_dir=SFX_DIR):
    """Pioche un SFX dont le chemin (sous-dossier ou nom) contient la catégorie.
    Ex: category='impact' matche le dossier 'Impacts/' ou un fichier 'impact_x.wav'."""
    cat = category.lower()
    cands = [f for f in list_sfx(sfx_dir)
             if cat in os.path.relpath(f, sfx_dir).lower()]
    return random.choice(cands) if cands else None
