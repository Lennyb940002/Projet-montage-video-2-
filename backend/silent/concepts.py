"""Parser du DOSSIER_CONCEPTS.md (source de vérité des textes, éditée par
l'utilisateur). Extrait par concept les pools `hook:` et `cta:`. L'engine
mappe une mécanique -> un code concept (SILENT['mechanic_concept']).

Fallback : si le fichier est absent, hooks_for() renvoie [] et le sous-système
hooks retombe sur les banques JSON intégrées."""
import os
import re
import functools
from backend.config import SILENT


def _slug(text):
    t = re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
    return re.sub(r"\s+", "_", t)[:32] or "hook"


@functools.lru_cache(maxsize=1)
def load_concepts(path=None):
    """{code: {'hooks': [...], 'cta': [...]}}. Vide si fichier introuvable."""
    path = path or SILENT.get("concepts_file")
    out = {}
    if not path or not os.path.isfile(path):
        return out
    code = None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if line.startswith("## "):
            code = line[3:].strip().split()[0]   # 1er token (ignore commentaires)
            out[code] = {"hooks": [], "cta": []}
        elif code and line.lstrip().startswith("-"):
            body = line.lstrip().lstrip("-").strip()
            low = body.lower()
            if low.startswith("hook:"):
                out[code]["hooks"] = [h.strip() for h in body[5:].split("|") if h.strip()]
            elif low.startswith("cta:"):
                out[code]["cta"] = [c.strip() for c in body[4:].split("|") if c.strip()]
    return out


def _concept_for(mechanic):
    return (SILENT.get("mechanic_concept") or {}).get(mechanic)


def hooks_for(mechanic):
    """[(text, angle)] depuis le dossier ; [] si indisponible (=> fallback JSON)."""
    code = _concept_for(mechanic)
    if not code:
        return []
    c = load_concepts().get(code)
    if not c or not c["hooks"]:
        return []
    return [(h, _slug(h)) for h in c["hooks"]]


def cta_for(mechanic):
    """Pool de CTA (pour la description/caption) ; [] si indisponible."""
    code = _concept_for(mechanic)
    c = load_concepts().get(code) if code else None
    return list(c["cta"]) if c and c.get("cta") else []
