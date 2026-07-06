"""Système de captions V2 — Flowers Chrome (L'Ascendant Magnétique).

La caption DÉPEND DU CONCEPT (bloc `editorial` : opening/value propres au sujet
du Reel), pas seulement de la famille. 4 blocs : ouverture · valeur · CTA unique
(lié au concept) · référencement discret (≤3 hashtags whitelist, nom du modèle
seulement si une seule montre). 2 modes : premium_short / conversion.

Preuve : soit un `proof` vérifié -> caption autorisée construite sur le fait ;
soit `requires_real_asset` -> BLOQUÉ, build() renvoie None (aucun texte publiable).

Gouverné par FAMILIES_V2 + cta_v2. Aucune fabrication, un seul CTA, voix je/tu."""
import re

from backend.silent import canon, cta_v2
from backend.distribution import caption_seo

MODE_BY_FAMILY = {
    "miroir": "premium_short", "projection": "premium_short",
    "revelation": "premium_short", "bascule": "premium_short",
    "choix_force": "conversion", "conseil": "conversion", "preuve": "conversion",
}

ALLOWED_HASHTAGS = ["#montre", "#montreautomatique", "#montrehomme", "#stylehomme",
                    "#montreaupoignet", "#flowerschrome", "#horlogerie"]
_ALLOWED_LOWER = {h.lower() for h in ALLOWED_HASHTAGS}

# Max 3 hashtags/caption. #horlogerie reste dans la whitelist mais n'est PAS
# utilisé par le batch V2 (audience plus technique que notre cœur de cible).
HASHTAGS_BY_FAMILY = {
    "miroir": ["#flowerschrome", "#montreautomatique", "#stylehomme"],
    "choix_force": ["#flowerschrome", "#montrehomme", "#montreautomatique"],
    "projection": ["#flowerschrome", "#montreaupoignet", "#stylehomme"],
    "bascule": ["#flowerschrome", "#stylehomme", "#montrehomme"],
    "revelation": ["#flowerschrome", "#montreautomatique"],
    "conseil": ["#flowerschrome", "#montreautomatique", "#montrehomme"],
    "preuve": ["#flowerschrome", "#montre"],
}

SIGMA_BLACKLIST = ("sigma", "mindset", "alpha", "discipline", "mentalité",
                   "développement personnel", "gamin", "vrai homme", "inférieur")
_HASHTAG_RE = re.compile(r"#\w+")
_DM_RE = re.compile(r"\bdm\b", re.IGNORECASE)


def is_blocked(concept):
    """True si le concept est une Preuve sans matière réelle -> aucune caption."""
    return bool(concept.get("requires_real_asset"))


def _seo_line(model_names):
    names = [n for n in (model_names or []) if n]
    # nom du modèle SEULEMENT si une seule montre (pas mécaniquement en multi-montres)
    return f"{names[0]} · montre automatique Flowers Chrome." if len(names) == 1 else ""


def _strip_forbidden_hashtags(text):
    return _HASHTAG_RE.sub(lambda m: m.group(0) if m.group(0).lower() in _ALLOWED_LOWER else "", text)


def _sanitize_lines(text):
    return "\n".join(canon.sanitize(line) for line in text.split("\n"))


def validate(text, concept, mode=None):
    """(ok, raison). Garde-fous obligatoires avant écriture."""
    fam, cta = concept["family_id"], concept["cta_type"]
    mode = mode or concept.get("caption_mode") or MODE_BY_FAMILY[fam]
    if not text or not text.strip():
        return False, "caption vide"
    if not canon.is_clean(text):
        return False, "terme Canon interdit / ancien nom de modèle"
    tags = _HASHTAG_RE.findall(text)
    if len(tags) > 3:
        return False, f"trop de hashtags ({len(tags)}>3)"
    if any(t.lower() not in _ALLOWED_LOWER for t in tags):
        return False, "hashtag non autorisé"
    dm_kw = ("«" in text) or bool(_DM_RE.search(text))
    if dm_kw and not cta_v2.uses_dm(cta):
        return False, "CTA DM/CHOIX interdit pour cette famille"
    if not dm_kw and cta_v2.uses_dm(cta):
        return False, "CTA DM attendu manquant"
    hook = (concept.get("hook") or "").strip().lower()
    if hook and hook in text.lower():
        return False, "hook recopié mot pour mot"
    low = text.lower()
    if any(b in low for b in SIGMA_BLACKLIST):
        return False, "formulation sigma/dev-perso interdite"
    if re.search(r"\d+\s*%", text):
        return False, "chiffre non vérifié (%)"
    if len(text) > (240 if mode == "premium_short" else 360):
        return False, f"trop long pour le mode {mode}"
    return True, "ok"


def _compose(concept, model_names, fam, mode):
    ed = concept.get("editorial") or {}
    opening = ed.get("opening", "").strip()
    if not opening:
        raise ValueError(f"editorial.opening manquant pour {concept['concept_id']}")
    value = ed.get("value", "").strip()
    cta = concept.get("cta_text") or cta_v2.caption(concept["cta_type"])
    hashtags = " ".join(HASHTAGS_BY_FAMILY[fam][:3])
    seo = _seo_line(model_names)
    seo_block = (f"{seo} {hashtags}" if seo else hashtags).strip()
    blocks = [canon.sanitize(opening)]
    if value:
        blocks.append(canon.sanitize(value))
    blocks.append(canon.sanitize(cta))
    blocks.append(canon.sanitize(seo_block))
    sep = "\n\n" if mode == "premium_short" else "\n"
    return _strip_forbidden_hashtags(sep.join(b for b in blocks if b))


def _gemini(concept, model_names, mode, key):
    ed = concept.get("editorial") or {}
    montres = ", ".join(n for n in (model_names or []) if n) or "la pièce"
    prompt = (
        "Rédige en FRANÇAIS une description Instagram pour « Flowers Chrome » "
        "(homme ambitieux qui monte, ton calme et sûr, voix je/tu).\n"
        f"Sujet précis : {ed.get('situation','')} — angle : {ed.get('angle','')}.\n"
        f"Montre(s) : {montres}. Ne recopie PAS l'accroche : \"{concept.get('hook','')}\".\n"
        f"Ouvre par : \"{ed.get('opening','')}\". Valeur : \"{ed.get('value','')}\". "
        f"UN SEUL CTA : \"{concept.get('cta_text') or cta_v2.caption(concept['cta_type'])}\". "
        f"Puis ≤3 hashtags parmi {HASHTAGS_BY_FAMILY[concept['family_id']]}.\n"
        f"Mode {mode}. " + canon.PROMPT_CONSTRAINT +
        " Aucun chiffre inventé, aucun faux avis, aucune promesse non vérifiée.")
    return caption_seo._gemini_generate(prompt, key)


def build(concept, model_names=None):
    """Caption V2 validée, ou None si concept BLOQUÉ (Preuve sans matière)."""
    if is_blocked(concept):
        return None
    fam = concept["family_id"]
    mode = concept.get("caption_mode") or MODE_BY_FAMILY[fam]
    key = caption_seo._gemini_key()
    if key:
        try:
            txt = _sanitize_lines(_strip_forbidden_hashtags(_gemini(concept, model_names, mode, key)))
            if validate(txt, concept, mode)[0]:
                return txt
        except Exception:
            pass
    return _compose(concept, model_names, fam, mode)
