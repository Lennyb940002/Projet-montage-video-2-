"""Détection des passages à valider sur une voix IA :
- 🟡 reprises : blocs de >=4 mots répétés à l'identique (begaiement toléré entre les deux)
- 🔴 mots peu sûrs : probabilité Whisper sous un seuil
"""
import re, difflib
from backend.config import DETECT

MINREP = 4   # longueur mini d'un bloc répété
MAXGAP = 5   # mots de "bégaiement" tolérés entre les deux occurrences

def _norm(w):
    return re.sub(r"[^0-9a-zàâäçéèêëîïôöùûüœæ]", "", w.lower())

def find_retakes(words):
    """Retourne [{i1, i2, start, end, text}] : couper les mots [i1, i2) (1ère
    occurrence + bégaiement), garder la 2ème."""
    n = len(words)
    norms = [_norm(w.text) for w in words]
    out = []
    i = 0
    while i < n:
        best = None
        maxL = (n - i) // 2
        for L in range(maxL, MINREP - 1, -1):
            for gap in range(0, MAXGAP + 1):
                j = i + L + gap
                if j + L > n:
                    continue
                if (norms[i:i+L] == norms[j:j+L] or
                        difflib.SequenceMatcher(a=norms[i:i+L], b=norms[j:j+L]).ratio()
                        >= DETECT["fuzzy_ratio"]) and all(norms[i:i+L]):
                    best = (L, gap, j)
                    break
            if best:
                break
        if best:
            L, gap, j = best
            out.append({"i1": i, "i2": j,
                        "start": words[i].start, "end": words[j].start,
                        "text": " ".join(w.text for w in words[i:j])})
            i = j
        else:
            i += 1
    return out

def low_confidence(words, threshold=None):
    """Indices des mots peu sûrs. Seuil RELATIF à la confiance moyenne si non fourni.
    Inclut les mots tronqués (prob basse ET durée anormalement courte)."""
    if not words:
        return []
    if threshold is None:
        mean = sum(w.prob for w in words) / len(words)
        threshold = max(0.35, min(0.55, mean - 0.2))
    out = {i for i, w in enumerate(words) if w.prob < threshold}
    for i, w in enumerate(words):
        if w.prob < 0.45 and (w.end - w.start) < 0.12:
            out.add(i)
    return sorted(out)

def long_pauses(words, min_gap=None):
    """Plages des silences résiduels anormalement longs entre deux mots."""
    g = DETECT["pause_min"] if min_gap is None else min_gap
    out = []
    for i in range(len(words) - 1):
        if words[i + 1].start - words[i].end >= g:
            out.append({"start": words[i].end, "end": words[i + 1].start})
    return out

def detect(words):
    return {"retakes": find_retakes(words),
            "lowconf": low_confidence(words),
            "pauses": long_pauses(words)}
