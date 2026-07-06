"""Renderer Stories V2 — DA « Nocturne réchauffé + Chrome » (cf docs/BRANDING_V2.md).

Templates : hero_model · minimal_text · choice · detail_macro · faq · proof_real ·
availability_verified · highlight_cover. 1080x1920, fond #070707, serif Fraunces,
monogramme FC discret. AUCUNE publication ici — rendu pur.

Règles câblées : un seul CTA par écran, texte hors cadran (bandes haut/bas),
pas d'emoji, pas de ❀, pas de prix barré, pas de « disponible » hors template
availability_verified (lui-même gated par verified_stock)."""
import base64
import json
import os
import re

from backend.config import PHOTOS
from backend.posts.carousel import _fonts_css

W, H = 1080, 1920
BLACK, GRAPHITE, CHROME, WHITE, AMBER = "#070707", "#18191B", "#C4C8CC", "#F2F3F4", "#C99645"

FACTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commercial_facts.json")
AVATAR_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "..", "..", "assets", "avatar", "fc_avatar_master.png"))
MONOGRAM_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "..", "..", "assets", "avatar",
                                             "fc_monogram_transparent.png"))


class MissingBrandAsset(RuntimeError):
    """Le monogramme validé est absent — AUCUN fallback typographique autorisé."""


def brand_asset():
    """(path, data_uri) du monogramme transparent (stories/watermarks). (None, None)
    si absent — le rendu doit alors ÉCHOUER (blocked_missing_brand_asset)."""
    if os.path.isfile(MONOGRAM_PATH):
        return MONOGRAM_PATH, _uri(MONOGRAM_PATH)
    return None, None

# model_id V2 -> préfixe des photos réelles (backend/Photo réel)
MODEL_PHOTO_PREFIX = {"aurora": "or_rose", "nocturne": "saphir", "braise": "ruby",
                      "eclipse": "silver", "meridien": "gmt"}
MODEL_NAMES = {"aurora": "FC Aurora", "nocturne": "FC Nocturne", "braise": "FC Braise",
               "eclipse": "FC Éclipse", "meridien": "FC Méridien"}

_FORBIDDEN = re.compile(r"[❀🚨🌴⬇️📩✅❌🔥💡📚⌚📈]|promo|barr[ée]|\d+\s*[,.]?\d*\s*€\s*❌", re.IGNORECASE)


def load_facts():
    with open(FACTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def fact_verified(facts, key):
    e = facts.get(key) or {}
    return e.get("status") == "verified" and e.get("value") not in (None, "", [])


PREFERRED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preferred_assets.json")


def _preferred(model_id):
    try:
        with open(PREFERRED_PATH, encoding="utf-8") as f:
            return (json.load(f).get(model_id) or {}).get("preferred_asset_id")
    except OSError:
        return None


def photo_for_model(model_id, index=0):
    """Photo héros du modèle : la sélection EXPLICITE (preferred_assets.json)
    d'abord ; fallback = 1re photo du préfixe. None si absente."""
    d = PHOTOS.get("dir")
    if not d or not os.path.isdir(d):
        return None
    pref = _preferred(model_id)
    if pref:
        for ext in (".jpeg", ".jpg", ".png", ".webp"):
            p = os.path.join(d, pref + ext)
            if os.path.isfile(p):
                return p
    prefix = MODEL_PHOTO_PREFIX.get(model_id)
    if not prefix:
        return None
    matches = sorted(f for f in os.listdir(d)
                     if f.lower().startswith(prefix) and
                     os.path.splitext(f)[1].lower() in (".jpg", ".jpeg", ".png", ".webp"))
    return os.path.join(d, matches[index % len(matches)]) if matches else None


def _uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def _page_css():
    return (f"{_fonts_css()}"
            f"*{{margin:0;padding:0;box-sizing:border-box;}}"
            f"html,body{{width:{W}px;height:{H}px;background:{BLACK};}}"
            f".story{{position:relative;width:{W}px;height:{H}px;background:{BLACK};"
            f"overflow:hidden;color:{WHITE};font-family:'Fraunces',Georgia,serif;}}"
            f".mono{{position:absolute;bottom:64px;left:0;right:0;text-align:center;"
            f"font-size:34px;letter-spacing:0.35em;color:{CHROME};opacity:0.85;}}"
            # CTA au-dessus de la zone basse 280px (interface Instagram)
            f".cta{{position:absolute;bottom:440px;left:0;right:0;text-align:center;"
            f"font-size:40px;color:{WHITE};letter-spacing:0.04em;}}"
            f".head{{font-weight:400;letter-spacing:0.14em;text-transform:uppercase;}}")


def _bg_photo(uri):
    return (f"<img style='position:absolute;inset:0;width:100%;height:100%;"
            f"object-fit:cover;' src='{uri}'/>"
            f"<div style='position:absolute;inset:0;background:"
            f"linear-gradient(180deg,rgba(7,7,7,.72) 0%,rgba(7,7,7,0) 26%,"
            f"rgba(7,7,7,0) 58%,rgba(7,7,7,.88) 100%);'></div>")


def _amber_line():
    return (f"<div style='position:absolute;left:50%;transform:translateX(-50%);"
            f"bottom:512px;width:120px;height:3px;background:{AMBER};opacity:.7;'></div>")


def _monogram():
    """Monogramme officiel — placement V1 UNIQUE sur tous les templates :
    coin inférieur droit, 80px, marge droite 64px, marge basse 320px.
    AUCUN fallback : master absent => MissingBrandAsset."""
    path, uri = brand_asset()
    if not uri:
        raise MissingBrandAsset("fc_monogram_transparent.png absent — déposer le master")
    return (f"<img class='monoimg' style='position:absolute;bottom:320px;right:64px;"
            f"width:80px;height:80px;object-fit:contain;opacity:.9;' src='{uri}'/>")


def _html(body):
    return f"<!DOCTYPE html><html><head><meta charset='UTF-8'><style>{_page_css()}</style></head><body><div class='story'>{body}</div></body></html>"


_DEBUG_OVERLAY = (
    f"<style>.story *{{outline:1px dashed rgba(255,90,90,.55);}}"
    f".dz{{outline:none !important;pointer-events:none;position:absolute;left:0;right:0;}}</style>"
    f"<div class='dz' style='top:0;height:220px;background:rgba(255,0,0,.16);'></div>"
    f"<div class='dz' style='bottom:0;height:280px;background:rgba(255,0,0,.16);'></div>"
    f"<div class='dz' style='bottom:150px;height:110px;border-top:2px solid {AMBER};"
    f"border-bottom:2px solid {AMBER};'></div>"
    f"<div class='dz' style='bottom:40px;height:120px;width:140px;left:50%;right:auto;"
    f"transform:translateX(-50%);border:2px solid #4FC3F7;'></div>")


def _tpl_hero_model(fr, photo):
    name = fr.get("on_screen_text") or MODEL_NAMES.get(fr.get("model_id"), "")
    sub = fr.get("subtext") or ""
    cta = fr.get("cta_text") or ""
    body = _bg_photo(_uri(photo))
    body += (f"<div class='head' style='position:absolute;top:250px;left:0;right:0;"
             f"text-align:center;font-size:64px;'>{name}</div>")
    if sub:
        body += (f"<div style='position:absolute;top:352px;left:0;right:0;text-align:center;"
                 f"font-size:38px;color:{CHROME};font-style:italic;'>{sub}</div>")
    if cta:
        body += _amber_line() + f"<div class='cta'>{cta}</div>"
    body += _monogram()
    return _html(body)


def _tpl_minimal_text(fr, _photo=None):
    head = fr["on_screen_text"]
    cta = fr.get("cta_text") or ""
    body = (f"<div style='position:absolute;top:44%;left:90px;right:90px;transform:translateY(-50%);"
            f"text-align:center;font-size:76px;line-height:1.3;'>{head}</div>")
    if cta and cta != head:
        body += _amber_line() + f"<div class='cta'>{cta}</div>"
    elif cta:
        body += _amber_line()
    body += _monogram()
    return _html(body)


def _tpl_choice(fr, photos):
    a, b = photos
    na = MODEL_NAMES.get(fr["model_id"][0], "A"); nb = MODEL_NAMES.get(fr["model_id"][1], "B")
    body = (f"<img style='position:absolute;top:0;left:0;width:100%;height:46%;object-fit:cover;' src='{_uri(a)}'/>"
            f"<img style='position:absolute;bottom:0;left:0;width:100%;height:46%;object-fit:cover;' src='{_uri(b)}'/>"
            f"<div style='position:absolute;top:46%;height:8%;left:0;right:0;background:{BLACK};"
            f"display:flex;align-items:center;justify-content:center;'>"
            f"<span class='head' style='font-size:44px;'>{fr['on_screen_text']}</span></div>"
            f"<div class='head' style='position:absolute;top:250px;left:60px;font-size:40px;color:{WHITE};"
            f"text-shadow:0 2px 18px rgba(0,0,0,.8);'>{na}</div>"
            f"<div class='head' style='position:absolute;bottom:310px;right:60px;font-size:40px;color:{WHITE};"
            f"text-shadow:0 2px 18px rgba(0,0,0,.8);'>{nb}</div>")
    return _html(body)


def _tpl_detail_macro(fr, photo):
    body = _bg_photo(_uri(photo))
    body += (f"<div class='head' style='position:absolute;bottom:360px;left:0;right:0;"
             f"text-align:center;font-size:52px;'>{fr['on_screen_text']}</div>")
    body += _monogram()
    return _html(body)


def _tpl_faq(fr, _photo=None):
    q = fr["on_screen_text"]; a = fr.get("subtext") or ""
    cta = fr.get("cta_text") or ""
    body = (f"<div style='position:absolute;top:30%;left:90px;right:90px;text-align:center;"
            f"font-size:66px;line-height:1.3;'>{q}</div>"
            f"<div style='position:absolute;top:52%;left:110px;right:110px;text-align:center;"
            f"font-size:44px;line-height:1.45;color:{CHROME};"
            f"font-family:Arial,Helvetica,sans-serif;'>{a}</div>")
    if cta:
        body += _amber_line() + f"<div class='cta'>{cta}</div>"
    body += _monogram()
    return _html(body)


def _tpl_proof_real(fr, photo):
    """Uniquement pour un ASSET RÉEL fourni. Texte minimal, la matière parle."""
    body = _bg_photo(_uri(photo))
    txt = fr.get("on_screen_text") or ""
    if txt:
        body += (f"<div class='head' style='position:absolute;bottom:360px;left:0;right:0;"
                 f"text-align:center;font-size:48px;'>{txt}</div>")
    cta = fr.get("cta_text") or ""
    if cta:
        body += f"<div class='cta'>{cta}</div>"
    body += _monogram()
    return _html(body)


def _tpl_availability(fr, photo):
    """Gated en AMONT par verified_stock — le template n'affiche que du vérifié."""
    body = _bg_photo(_uri(photo))
    body += (f"<div class='head' style='position:absolute;top:260px;left:0;right:0;"
             f"text-align:center;font-size:58px;'>{fr['on_screen_text']}</div>")
    body += _amber_line() + f"<div class='cta'>{fr.get('cta_text','')}</div>" + _monogram()
    return _html(body)


def _framed_window(uri, top, height):
    """Photo CONTENUE dans une fenêtre maîtrisée sur fond noir réel — aucun
    assombrissement artificiel de la montre (pas de gradient sur la photo)."""
    return (f"<div style='position:absolute;top:{top}px;left:100px;right:100px;height:{height}px;"
            f"border:1px solid {GRAPHITE};overflow:hidden;'>"
            f"<img style='width:100%;height:100%;object-fit:cover;' src='{uri}'/></div>")


def _tpl_hero_model_framed(fr, photo):
    """Variante B — Cadre Nocturne : fond #070707 réel, photo en fenêtre,
    texte placé sur le fond noir (jamais sur la photo), espace négatif."""
    name = fr.get("on_screen_text") or MODEL_NAMES.get(fr.get("model_id"), "")
    sub = fr.get("subtext") or ""
    cta = fr.get("cta_text") or ""
    body = (f"<div class='head' style='position:absolute;top:250px;left:0;right:0;"
            f"text-align:center;font-size:60px;'>{name}</div>")
    if sub:
        body += (f"<div style='position:absolute;top:350px;left:0;right:0;text-align:center;"
                 f"font-size:36px;color:{CHROME};font-style:italic;'>{sub}</div>")
    body += _framed_window(_uri(photo), 450, 940)
    if cta:
        body += _amber_line() + f"<div class='cta'>{cta}</div>"
    body += _monogram()
    return _html(body)


def _tpl_detail_macro_framed(fr, photo):
    body = (f"<div class='head' style='position:absolute;top:260px;left:0;right:0;"
            f"text-align:center;font-size:52px;'>{fr['on_screen_text']}</div>")
    body += _framed_window(_uri(photo), 430, 960)
    body += _monogram()
    return _html(body)


TEMPLATES = {"hero_model": _tpl_hero_model, "minimal_text": _tpl_minimal_text,
             "choice": _tpl_choice, "detail_macro": _tpl_detail_macro,
             "faq": _tpl_faq, "proof_real": _tpl_proof_real,
             "availability_verified": _tpl_availability,
             "hero_model_framed": _tpl_hero_model_framed,
             "detail_macro_framed": _tpl_detail_macro_framed}


def check_frame_text(fr):
    """Garde-fou éditorial : pas d'emoji/❀/promo/prix barré dans les textes."""
    for k in ("on_screen_text", "subtext", "cta_text"):
        v = fr.get(k) or ""
        if _FORBIDDEN.search(v):
            return False
    return True


def render_frame(fr, out_path, photo=None, debug=False):
    """Rend une frame -> PNG. `photo` = chemin (ou paire pour choice).
    `debug=True` : superpose safe-zones (haut 220 / bas 280 / bande CTA /
    position monogramme) + bounding boxes de tous les éléments. NON publiable."""
    from playwright.sync_api import sync_playwright
    tpl = fr["template_id"]
    # Décision V1 : photos actuelles TOUJOURS en Cadre Nocturne (full_bleed
    # conservé dans le code mais hors mix — retour explicite par asset plus tard).
    if fr.get("presentation_mode") == "nocturne_frame":
        tpl = {"hero_model": "hero_model_framed",
               "detail_macro": "detail_macro_framed"}.get(tpl, tpl)
    fn = TEMPLATES.get(tpl)
    if fn is None:
        raise ValueError(f"template inconnu: {tpl!r}")
    if not check_frame_text(fr):
        raise ValueError(f"texte interdit (emoji/promo/❀) dans {fr['frame_id']}")
    html = fn(fr, photo)
    if debug:
        html = html.replace("</div></body>", _DEBUG_OVERLAY + "</div></body>")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_context(viewport={"width": W, "height": H}).new_page()
        page.set_content(html, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(350)
        page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
    return out_path
