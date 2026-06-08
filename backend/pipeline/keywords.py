"""Détection d'évènements normalisés à partir des tokens.

Aucune décision de montage ici. Renvoie une liste d'Event :
    {"type": "keyword", "label": str, "start": float, "end": float, "importance": str}

Le Director consomme ces évènements pour produire le plan.
"""
from backend.pipeline.sfx_plan import (is_price, is_number, is_watch_brand,
                                       is_question_word, is_cta, _norm)

SUPERLATIVES = {"incroyable", "jamais", "fou", "folle", "énorme", "dingue", "ouf",
                "record", "exceptionnel", "rare", "unique", "meilleur", "luxe",
                "premium", "gratuit", "exclusif", "magnifique", "parfait"}

def _classify(text):
    """Renvoie (is_kw, importance) pour un mot."""
    if is_price(text) or is_watch_brand(text):
        return True, "high"
    if is_number(text) or is_cta(text):
        return True, "high"
    if is_question_word(text):
        return True, "normal"
    if _norm(text) in SUPERLATIVES:
        return True, "high"
    return False, None

def detect_events(tokens, ranges=None):
    """Détecte et classe les évènements à partir des tokens (et optionnellement
    des plages de clips, pour des évènements "cut" futurs)."""
    events = []
    for t in tokens:
        is_kw, importance = _classify(t["disp"])
        if is_kw:
            events.append({
                "type": "keyword",
                "label": t["disp"],
                "start": t["start"],
                "end": t["end"],
                "importance": importance,
            })
    return events
