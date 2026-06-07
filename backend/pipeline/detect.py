"""Détection des passages à valider sur une voix IA :
- 🟡 reprises : blocs de >=4 mots répétés à l'identique (begaiement toléré entre les deux)
- 🔴 mots peu sûrs : probabilité Whisper sous un seuil
"""
import re

MINREP = 4   # longueur mini d'un bloc répété
MAXGAP = 5   # mots de "bégaiement" tolérés entre les deux occurrences
LOWCONF = 0.5

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
                if norms[i:i+L] == norms[j:j+L] and all(norms[i:i+L]):
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

def low_confidence(words, threshold=LOWCONF):
    """Indices des mots dont la probabilité est sous le seuil."""
    return [i for i, w in enumerate(words) if w.prob < threshold]

def detect(words):
    return {"retakes": find_retakes(words), "lowconf": low_confidence(words)}
