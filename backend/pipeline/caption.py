import re
from backend.config import (DEFAULT_CTA, BASE_HASHTAGS, DEFAULT_BENEFITS,
                            BENEFIT_KEYWORDS, BRAND_TAGS)

CTA_VERBS = ("écris", "ecris", "commente", "commande", "abonne", "suis", "clique")

def _sentences(text):
    parts = re.split(r"(?<=[.!?…])\s+", text.replace("\n", " ").strip())
    return [p.strip() for p in parts if p.strip()]

def _is_cta(s):
    sl = s.lower()
    return any(v in sl for v in CTA_VERBS)

def _is_benefit(s):
    sl = s.lower()
    return any(k in sl for k in BENEFIT_KEYWORDS)

def generate_caption(text):
    sents = _sentences(text)
    accroche = sents[0] if sents else ""
    cta = next((s for s in sents if _is_cta(s)), DEFAULT_CTA)
    benefits = [s for s in sents[1:] if _is_benefit(s) and s != cta][:3]
    benefits = ["✅ " + b for b in benefits] or list(DEFAULT_BENEFITS)

    tl = text.lower()
    tags = list(BASE_HASHTAGS)
    for brand, tag in BRAND_TAGS.items():
        if re.search(r"\b" + re.escape(brand) + r"\b", tl) and tag not in tags:
            tags.append(tag)
    seen = set(); hashtags = []
    for t in tags:
        if t not in seen:
            seen.add(t); hashtags.append(t)
    hashtags = hashtags[:12]

    lines = []
    if accroche:
        lines.append(accroche)
    if benefits:
        lines += ["", *benefits]
    lines += ["", cta]
    description = "\n".join(lines).strip()
    full = (description + "\n\n" + " ".join(hashtags)).strip()
    return {"description": description, "hashtags": hashtags, "full": full}
