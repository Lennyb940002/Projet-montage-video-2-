from backend.pipeline.sfx_plan import (is_price, is_number, is_watch_brand,
                                       is_question_word, is_cta, _norm)

SUPERLATIVES = {"incroyable", "jamais", "fou", "folle", "énorme", "dingue", "ouf",
                "record", "exceptionnel", "rare", "unique", "meilleur", "luxe",
                "premium", "gratuit", "exclusif", "magnifique", "parfait"}

def is_keyword(text):
    return (is_price(text) or is_number(text) or is_watch_brand(text)
            or is_cta(text) or is_question_word(text) or _norm(text) in SUPERLATIVES)

def mark(tokens):
    """Annote chaque token : t['kw'] = mot à forte valeur. Retourne tokens."""
    for t in tokens:
        t["kw"] = is_keyword(t["disp"])
    return tokens
