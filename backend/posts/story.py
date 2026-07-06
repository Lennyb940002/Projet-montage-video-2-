"""Renderer story « partage de contenu » (1080x1920) — template officiel :
  - zone haute 15 % : accroche courte (rotation)
  - zone centrale 70 % : le contenu partagé (slide carrousel / frame vidéo), lisible
  - zone basse 15 % : CTA orienté DM (rotation obligatoire)
Fond sombre, texte blanc, police simple, premium. Rendu via Playwright (emoji OK).
"""
import base64
import os
from playwright.sync_api import sync_playwright

W, H = 1080, 1920

# Accroches (zone haute) — une seule phrase, rotation.
HOOKS = [
    "🚨 Nouvelle vidéo", "📚 Nouveau conseil", "💡 Nouvelle astuce",
    "🔥 Nouveau contenu", "⌚ Nouvelle analyse", "📈 À ne pas manquer",
]

# CTA (zone basse) — toujours orienté message privé, rotation obligatoire.
CTAS = [
    "📩 DM « MONTRE » pour voir les modèles",
    "📩 DM pour recevoir le catalogue",
    "📩 Besoin d'aide pour choisir ? Écris-moi",
    "📩 DM « CHOIX » et je te conseille un modèle",
    "📩 Tu cherches une montre ? Écris-moi",
    "📩 DM pour découvrir les nouveautés",
    "📩 Une question sur un modèle ? Écris-moi",
    "📩 DM « INFO » pour plus de détails",
    "📩 Je peux t'aider à trouver la bonne montre",
    "📩 DM pour voir toute la collection",
    "📩 Besoin d'un conseil ? Message privé",
    "📩 DM pour connaître les disponibilités",
    "📩 Je réponds à tout en privé",
    "📩 DM si un modèle t'intéresse",
    "📩 Tu hésites ? Écris-moi",
]


def pick_hook(n):
    return HOOKS[n % len(HOOKS)]


def pick_cta(n):
    return CTAS[n % len(CTAS)]


def _img_data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def _html(content_uri, hook, cta):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:{W}px;height:{H}px;background:#050505;}}
.story{{width:{W}px;height:{H}px;background:#050505;display:flex;flex-direction:column;
 font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#fff;overflow:hidden;}}
.top{{height:15%;display:flex;align-items:center;justify-content:center;padding:0 90px;}}
.top span{{font-size:50px;font-weight:600;letter-spacing:0.01em;text-align:center;}}
.mid{{height:70%;display:flex;align-items:center;justify-content:center;padding:0 60px;}}
.mid img{{max-width:100%;max-height:100%;border-radius:28px;
 box-shadow:0 0 0 1px rgba(255,255,255,0.08);}}
.bot{{height:15%;display:flex;align-items:center;justify-content:center;padding:0 80px;}}
.bot span{{font-size:38px;font-weight:500;text-align:center;color:#f2f2f2;}}
</style></head><body>
<div class="story">
  <div class="top"><span>{hook}</span></div>
  <div class="mid"><img src="{content_uri}"/></div>
  <div class="bot"><span>{cta}</span></div>
</div></body></html>"""


def _cta_html(headline, sub, cta):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:{W}px;height:{H}px;background:#050505;}}
.story{{width:{W}px;height:{H}px;background:#050505;display:flex;flex-direction:column;
 justify-content:center;text-align:center;padding:0 110px;
 font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#fff;}}
.brand{{position:absolute;top:90px;left:0;right:0;text-align:center;font-size:34px;
 letter-spacing:0.06em;color:#f2f2f2;}}
.head{{font-size:74px;font-weight:600;line-height:1.15;}}
.sub{{font-size:40px;font-weight:400;color:#b8b8b8;margin-top:36px;line-height:1.35;}}
.cta{{position:absolute;bottom:150px;left:0;right:0;text-align:center;font-size:46px;font-weight:600;}}
</style></head><body>
<div class="story">
  <div class="brand">❀ Flowers Chrome ❀</div>
  <div class="head">{headline}</div>
  <div class="sub">{sub}</div>
  <div class="cta">{cta}</div>
</div></body></html>"""


def _promo_html(photo_uri, old_price, new_price):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:{W}px;height:{H}px;background:#000;}}
.story{{position:relative;width:{W}px;height:{H}px;overflow:hidden;
 font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;}}
.bg{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;}}
.lbl{{display:inline-block;background:#fff;color:#0a0a0a;font-weight:700;
 border-radius:22px;padding:14px 34px;line-height:1.12;}}
.top{{position:absolute;top:150px;left:50%;transform:translateX(-50%);
 font-size:64px;white-space:nowrap;}}
.group{{position:absolute;bottom:340px;left:0;right:0;display:flex;flex-direction:column;
 align-items:center;gap:26px;}}
.group .lbl{{font-size:62px;}}
</style></head><body>
<div class="story">
  <img class="bg" src="{photo_uri}"/>
  <span class="lbl top">🚨 Promo d'été 🌴</span>
  <div class="group">
    <span class="lbl">Disponible ✅</span>
    <span class="lbl">{old_price} ❌ {new_price} ✅</span>
    <span class="lbl">Go DM ⬇️</span>
  </div>
</div></body></html>"""


def render_promo_story(out_path, photo_path, old_price="194,50", new_price="179 euros"):
    """Story promo style IG natif : photo plein écran + pastilles blanches (texte noir)."""
    uri = _img_data_uri(photo_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_context(viewport={"width": W, "height": H}).new_page()
        page.set_content(_promo_html(uri, old_price, new_price), wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
    return out_path


def render_cta_story(out_path, headline, sub, cta):
    """Story CTA pure (sans contenu repris) : message + appel au DM."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_context(viewport={"width": W, "height": H}).new_page()
        page.set_content(_cta_html(headline, sub, cta), wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
    return out_path


def render_story(content_image, out_path, hook=None, cta=None, n=0):
    """Compose une story 1080x1920 autour de `content_image` (slide/frame).
    `n` = compteur de rotation (sélectionne accroche + CTA). Renvoie out_path."""
    hook = hook or pick_hook(n)
    cta = cta or pick_cta(n)
    uri = _img_data_uri(content_image)
    html = _html(uri, hook, cta)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_context(viewport={"width": W, "height": H}).new_page()
        page.set_content(html, wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=out_path, clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
    return out_path
