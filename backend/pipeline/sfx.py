import os, glob, random
from backend.config import SFX_DIR

def list_sfx(sfx_dir=SFX_DIR):
    if not os.path.isdir(sfx_dir):
        return []
    files = []
    for ext in ("*.wav", "*.mp3"):
        files += glob.glob(os.path.join(sfx_dir, ext))
    return sorted(files)

def pick(category, sfx_dir=SFX_DIR):
    cat = category.lower()
    cands = [f for f in list_sfx(sfx_dir) if cat in os.path.basename(f).lower()]
    return random.choice(cands) if cands else None
