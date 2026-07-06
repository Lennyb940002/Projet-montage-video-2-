"""CTA par famille (V2). UN seul CTA principal à l'écran + un CTA de caption
compatible, avec fallback propre par type. Système anti-« DM CHOIX partout » :
seuls les types dm_choix / proof_action utilisent CHOIX (cf docs/BRANDING_V2.md).

Types canoniques : comment · profile_visit · save_share · dm_choix · proof_action."""

CTA = {
    "comment":       {"screen": "Dis-moi laquelle tu gardes",
                      "caption": "Dis-moi laquelle tu gardes."},
    "profile_visit": {"screen": "Collection sur le profil",
                      "caption": "La collection est sur le profil."},
    "save":          {"screen": "Enregistre l'idée",
                      "caption": "Enregistre l'idée pour ta prochaine tenue."},
    "share":         {"screen": "Partage-la",
                      "caption": "Partage à celui qui vise le même cap."},
    "dm_choix":      {"screen": "Écris « CHOIX » en DM",
                      "caption": "DM « CHOIX » et je t'oriente."},
    "proof_action":  {"screen": "Écris-moi en DM",
                      "caption": "Dispo — écris-moi en DM."},
}
_FALLBACK = {"screen": "Découvre en bio", "caption": "Tout est sur le profil."}
VALID = frozenset(CTA)


def resolve(cta_type):
    """(texte écran, ligne caption) pour un type. Fallback propre si inconnu."""
    c = CTA.get(cta_type) or _FALLBACK
    return c["screen"], c["caption"]


def screen(cta_type):
    return resolve(cta_type)[0]


def caption(cta_type):
    return resolve(cta_type)[1]


def uses_dm(cta_type):
    """True si ce type sollicite le DM (CHOIX). Sert de garde-fou : on n'injecte
    jamais un CTA DM dans une famille non-DM."""
    return cta_type in ("dm_choix", "proof_action")
