"""Génère une caption SEO (FR) + 1-2 hashtags depuis les montres + la mécanique.
Gemini si clé dispo, sinon fallback template. JAMAIS bloquant."""
import re
import httpx
from backend import settings

GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              "gemini-2.0-flash:generateContent")


def _gemini_key():
    return settings.load().get("gemini_key") or None


def _gemini_generate(prompt, key):
    r = httpx.post(f"{GEMINI_URL}?key={key}",
                   json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
    j = r.json()
    return j["candidates"][0]["content"]["parts"][0]["text"]


def _prompt(mechanic, model_names, hook):
    montres = ", ".join(model_names)
    return (
        "Tu es expert SEO réseaux sociaux horlogers. Rédige en FRANÇAIS une "
        "description Instagram/TikTok optimisée SEO pour une vidéo de montres.\n"
        f"Mécanique: {mechanic}. Accroche à l'écran: \"{hook}\". Montres: {montres}.\n"
        "Contraintes: ton premium, intègre les noms exacts des montres et des "
        "mots-clés horlogers, 2-3 phrases max, puis EXACTEMENT 1 à 2 hashtags "
        "pertinents (pas plus). Termine par la ligne des hashtags.")


def _split_caption_hashtags(text):
    tags = re.findall(r"#\w+", text)[:2]
    body = re.sub(r"#\w+", "", text).strip()
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body, tags


def _fallback(mechanic, model_names, hook):
    montres = " vs ".join(model_names) if len(model_names) > 1 else (model_names[0] if model_names else "cette montre")
    body = f"{hook} {montres}. Dis-nous en commentaire 👇"
    return body, ["#montre", "#seiko"]


def build_caption(mechanic, model_names, hook):
    """Renvoie (caption:str, hashtags:list[str] de longueur 1-2)."""
    key = _gemini_key()
    if key:
        try:
            txt = _gemini_generate(_prompt(mechanic, model_names, hook), key)
            body, tags = _split_caption_hashtags(txt)
            if body and tags:
                return body, tags[:2]
        except Exception:
            pass
    return _fallback(mechanic, model_names, hook)
