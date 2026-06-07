import os, glob, random, re, array, subprocess
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

def choose(category, sfx_dir=SFX_DIR, lo=0.05, hi=1e9):
    """Choisit UN son cohérent dans la fenêtre de durée [lo, hi] (sinon le plus proche).
    Déterministe -> même son réutilisé dans toute la vidéo."""
    cands = _in_category(category, sfx_dir)
    if not cands:
        return None
    durs = {f: ffmpeg.probe_duration(f) for f in cands}
    inwin = [f for f in cands if lo <= durs[f] <= hi]
    if inwin:
        return min(inwin, key=lambda f: durs[f])      # le plus court dans la fenêtre
    # sinon : le plus proche de la fenêtre
    mid = (lo + hi) / 2 if hi < 1e9 else lo
    return min(cands, key=lambda f: abs(durs[f] - mid))

def peak_time(path):
    """Instant (s) du pic d'amplitude du fichier (pour caler le pic sur le cut)."""
    r = subprocess.run([ffmpeg.FFMPEG, "-v", "quiet", "-i", path,
                        "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True)
    raw = r.stdout
    if not raw:
        return 0.0
    s = array.array("h"); s.frombytes(raw[:len(raw) // 2 * 2])
    if not s:
        return 0.0
    mi = 0; mv = 0
    for i, v in enumerate(s):
        a = v if v >= 0 else -v
        if a > mv:
            mv = a; mi = i
    return mi / 8000.0

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
