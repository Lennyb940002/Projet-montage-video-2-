"""Garde-fous de génération — Canon V1 (cf docs/STRATEGIE_CANON.md).

Source UNIQUE des contraintes appliquées à TOUT texte généré par la machine
(hooks, captions, CTA, DM). Vrai jusqu'à preuve du contraire : on modifie ici,
et c'est appliqué partout automatiquement sur toutes les futures vidéos.

Décision V1 : on ne met jamais « mod / Seiko Daytona / DIY / jargon technique »
dans la communication — ça réduit la valeur perçue et pousse le primo-acheteur
vers le seuil de rejet (DIY/puriste)."""
import re

# --- Lexique banni (signaux réplique + termes qui poussent vers le DIY/puriste) ---
# Regex robustes : \b évite les faux positifs (« modèle », « mode », « commode »…).
_BANNED = [
    r"seiko\s+daytona",
    r"\bdaytona\b",
    r"\bdatejust\b",
    r"\bmod(?:s|d[ée]e?s?|ded)?\b",   # mod, mods, moddée, modded — PAS « modèle/mode »
    r"\bskx\b",
    r"\bfranken\w*",
    r"\bDIY\b",
    r"#seiko\w*",                     # #seiko, #seikomod, #seikomods…
    # hashtags de marques de luxe utilisés pour détourner l'audience -> bannis
    r"#(?:rolex|omega|patek\w*|audemars\w*|cartier|submariner|hublot|breitling|tissot|tagheuer|richardmille)\b",
]
_BANNED_RE = re.compile("|".join(_BANNED), re.IGNORECASE)

# Remplacements doux (filet de sécurité si un terme banni a déjà été écrit).
_REPLACE = [
    (re.compile(r"seiko\s+daytona(?:\s+\w+){0,2}", re.IGNORECASE), "notre montre"),
    (re.compile(r"\b(daytona|datejust)\b", re.IGNORECASE), "cette pièce"),
    (re.compile(r"#seiko\w*", re.IGNORECASE), "#horlogerie"),
    (re.compile(r"#(?:rolex|omega|patek\w*|audemars\w*|cartier|submariner|hublot|"
                r"breitling|tissot|tagheuer|richardmille)\b", re.IGNORECASE), ""),
    (re.compile(r"\bmod(?:s|d[ée]e?s?|ded)?\b", re.IGNORECASE), "montre"),
]


def violations(text):
    """Liste des termes bannis trouvés. Vide = conforme Canon V1."""
    return _BANNED_RE.findall(text or "")


def is_clean(text):
    return not _BANNED_RE.search(text or "")


def sanitize(text):
    """Rend un texte conforme Canon V1 (retire/remplace tout terme banni)."""
    if not text:
        return text
    for rgx, rep in _REPLACE:
        text = rgx.sub(rep, text)
    text = _BANNED_RE.sub("", text)              # filet dernier recours
    return re.sub(r"\s{2,}", " ", text).strip()


def sanitize_tags(tags):
    """Nettoie une liste de hashtags (retire #seiko & co, dédoublonne)."""
    out, seen = [], set()
    for t in tags or []:
        t = sanitize(t).strip()
        if t.startswith("#") and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


# Contrainte injectée dans les prompts de génération (Gemini & co).
PROMPT_CONSTRAINT = (
    "RÈGLES ABSOLUES : n'utilise JAMAIS les mots « Seiko Daytona », « Daytona », "
    "« Datejust », « mod », « SKX », « DIY » ni aucun jargon technique/mécanique. "
    "Reste sur l'IDENTITÉ, le style et le premium accessible (goût, pas frime). "
    "Vends le ressenti et ce que la montre dit de celui qui la porte, jamais la fiche technique."
)
