import os, glob, random, re
from backend import ffmpeg
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

def _in_category(category, sfx_dir):
    cat = category.lower()
    return [f for f in list_sfx(sfx_dir)
            if cat in os.path.relpath(f, sfx_dir).lower()]

def pick(category, sfx_dir=SFX_DIR):
    """Pioche un SFX (aléatoire) dont le chemin contient la catégorie."""
    cands = _in_category(category, sfx_dir)
    return random.choice(cands) if cands else None

def choose(category, sfx_dir=SFX_DIR, prefer_max=1.6):
    """Choisit UN son cohérent et 'punchy' : le plus court parmi ceux <= prefer_max s
    (sinon le plus court tout court). Déterministe -> même son réutilisé dans la vidéo."""
    cands = _in_category(category, sfx_dir)
    if not cands:
        return None
    durs = {f: ffmpeg.probe_duration(f) for f in cands}
    short = [f for f in cands if 0.1 <= durs[f] <= prefer_max]
    pool = short or cands
    return min(pool, key=lambda f: durs[f])

def onset(path, thresh="-30dB"):
    """Durée de 'lead-in' avant que le son démarre vraiment (silence/montée initiale).
    Sert à caler l'attaque d'un impact pile sur l'évènement."""
    r = ffmpeg.run([ffmpeg.FFMPEG, "-i", path, "-af",
                    f"silencedetect=noise={thresh}:d=0.02", "-f", "null", "-"])
    starts0 = re.search(r"silence_start:\s*0(\.0+)?\b", r.stderr)
    end = re.search(r"silence_end:\s*([0-9.]+)", r.stderr)
    if starts0 and end:
        return min(1.0, float(end.group(1)))
    return 0.0
