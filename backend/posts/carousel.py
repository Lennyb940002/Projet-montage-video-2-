"""Renderer carrousel valeur Flowers Chrome (1080x1350) via Playwright/Chromium.

Porté du brief FLOWERS_CHROME_POSTS_EDUCATION.md. Le CONTENU (textes des 5 slides)
est séparé du THÈME (coloris) : 3 coloris au choix — dark / light / pink.
Les polices sont embarquées en base64 (dossier ./fonts) — pas d'accès réseau.

API principale :
    render_carousel(content, theme="dark", out_dir=..., prefix=...) -> [png_paths]
content : dict (voir REFERENCE_CONTENT) ; sera produit par Gemini plus tard.
"""
import os
from functools import lru_cache
from playwright.sync_api import sync_playwright

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H = 1080, 1350

# --------------------------------------------------------------------------- #
# Polices base64
# --------------------------------------------------------------------------- #
def _font(key):
    with open(os.path.join(FONTS_DIR, f"fonts_b64_{key}.txt")) as f:
        return f.read().strip()


@lru_cache(maxsize=1)
def _fonts_css():
    g, s3, s4 = _font("goth"), _font("serif_300"), _font("serif_400")
    s3i, s4i = _font("serif_300_it"), _font("serif_400_it")
    m4, m5 = _font("mono_400"), _font("mono_500")
    def face(fam, w, st, b64):
        return (f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:{st};"
                f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
    return "".join([
        face("UnifrakturCook", 700, "normal", g),
        face("Fraunces", 300, "normal", s3), face("Fraunces", 400, "normal", s4),
        face("Fraunces", 300, "italic", s3i), face("Fraunces", 400, "italic", s4i),
        face("JetBrains Mono", 400, "normal", m4), face("JetBrains Mono", 500, "normal", m5),
    ])


# --------------------------------------------------------------------------- #
# Thèmes (3 coloris)
# --------------------------------------------------------------------------- #
THEMES = {
    "dark":  dict(ink="#ffffff", paper="#050505", hair="#1f1f1f", mute="#6a6a6a",
                  accent="#cfcfcf", vsb="#2a2a2a", tint="rgba(255,255,255,0.02)",
                  fili="ffffff", fili_op="0.035"),
    "light": dict(ink="#0a0a0a", paper="#fafafa", hair="#e2e2e2", mute="#8a8a8a",
                  accent="#454545", vsb="#dcdcdc", tint="rgba(0,0,0,0.02)",
                  fili="0a0a0a", fili_op="0.045"),
    "pink":  dict(ink="#ffffff", paper="#c4486f", hair="rgba(255,255,255,0.22)",
                  mute="rgba(255,255,255,0.62)", accent="rgba(255,255,255,0.88)",
                  vsb="rgba(255,255,255,0.28)", tint="rgba(255,255,255,0.06)",
                  fili="ffffff", fili_op="0.05"),
}
THEME_ORDER = ["dark", "light"]   # rotation noir / blanc (rose retiré)


def _root(t):
    """Bloc :root + filigrane (couleurs injectées selon le thème)."""
    fili = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' "
            "viewBox='0 0 100 100'><path d='M50 8 L50 92 M50 30 C42 30 38 22 38 18 "
            "C38 22 30 22 26 26 C30 26 30 30 34 34 L46 34 L46 50 L26 50 C22 50 18 46 "
            "14 50 C18 50 22 54 26 54 L46 54 L46 92 L54 92 L54 54 L74 54 C78 54 82 50 "
            "86 50 C82 50 78 46 74 50 L54 50 L54 34 L66 34 C70 30 70 26 74 26 C70 22 "
            "62 22 62 18 C62 22 58 30 50 30 Z' fill='none' stroke='%23" + t["fili"] +
            "' stroke-width='0.6'/></svg>")
    return (
        ":root{"
        f"--ink:{t['ink']};--paper:{t['paper']};--hair:{t['hair']};--mute:{t['mute']};"
        f"--accent:{t['accent']};--vsb:{t['vsb']};--tint:{t['tint']};"
        "--serif:'Fraunces',Georgia,serif;--mono:'JetBrains Mono',ui-monospace,monospace;"
        "--goth:'UnifrakturCook','Fraunces',serif;}"
        ".post::before{content:\"\";position:absolute;inset:0;background-image:url(\""
        + fili + "\");background-repeat:no-repeat;background-position:center;"
        f"background-size:90% 90%;opacity:{t['fili_op']};}}"
    )


CSS_BODY = """
*{box-sizing:border-box;margin:0;padding:0;}
html,body{width:1080px;height:1350px;background:var(--paper);-webkit-font-smoothing:antialiased;}
body{font-family:var(--serif);color:var(--ink);overflow:hidden;}
.post{width:1080px;height:1350px;background:var(--paper);position:relative;overflow:hidden;}
.corner-mark{position:absolute;color:var(--ink);z-index:5;font-family:var(--goth);}
.corner-mark.tl{top:44px;left:56px;font-size:36px;letter-spacing:-0.04em;}
.corner-mark.tr{top:44px;right:56px;}
.corner-mark.bl{bottom:44px;left:56px;}
.corner-mark.br{bottom:44px;right:56px;font-size:22px;letter-spacing:0.04em;}
.corner-mark svg{width:28px;height:28px;display:block;fill:var(--ink);}
.brand-banner{position:absolute;top:50px;left:50%;transform:translateX(-50%);
 font-family:var(--goth);font-size:30px;color:var(--ink);z-index:5;display:flex;align-items:center;gap:14px;}
.brand-banner svg{width:12px;height:12px;fill:var(--ink);}
.slide-num{position:absolute;top:130px;left:50%;transform:translateX(-50%);
 font-family:var(--mono);font-size:13px;letter-spacing:0.5em;text-transform:uppercase;color:var(--mute);z-index:5;}
.swipe-cue{position:absolute;bottom:120px;left:50%;transform:translateX(-50%);
 font-family:var(--mono);font-size:11px;letter-spacing:0.5em;text-transform:uppercase;color:var(--mute);
 display:flex;align-items:center;gap:12px;z-index:5;}
.swipe-cue svg{width:36px;height:14px;stroke:currentColor;}
.content{position:relative;z-index:2;height:100%;width:100%;padding:220px 110px 200px;
 display:flex;flex-direction:column;justify-content:center;}
.slide-1 .content{align-items:center;text-align:center;justify-content:center;}
.kicker{font-family:var(--mono);font-size:16px;letter-spacing:0.5em;text-transform:uppercase;color:var(--mute);margin-bottom:50px;}
.question-title{font-family:var(--goth);font-size:92px;line-height:1.02;color:var(--ink);}
.question-title em{font-style:italic;}
.divider-line{width:60px;height:1px;background:var(--ink);margin:40px auto;opacity:0.4;}
.big-price{font-family:var(--goth);font-size:200px;line-height:1;color:var(--ink);}
.slide-title{font-family:var(--goth);font-size:56px;line-height:1;margin-bottom:50px;color:var(--ink);}
.slide-title.smaller{font-size:46px;}
.slide-title em{font-style:italic;}
.body-text{font-family:var(--serif);font-weight:300;font-size:32px;line-height:1.55;color:var(--ink);}
.body-text strong{font-weight:400;}
.body-text em{font-style:italic;font-weight:400;}
.body-text p{margin-bottom:26px;}
.body-text p:last-child{margin-bottom:0;}
.bullets{list-style:none;margin:20px 0 0;padding:0;}
.bullets li{display:flex;gap:16px;align-items:baseline;font-family:var(--serif);font-weight:300;font-size:32px;line-height:1.4;color:var(--ink);margin-bottom:16px;}
.bullets li:last-child{margin-bottom:0;}
.bullets .mk{color:var(--accent);font-family:var(--mono);font-size:26px;flex:0 0 auto;}
.vs-block{display:flex;flex-direction:column;margin:30px 0;border:1px solid var(--vsb);}
.vs-row{display:flex;align-items:stretch;}
.vs-cell{flex:1;padding:24px 26px;font-family:var(--mono);font-size:18px;letter-spacing:0.08em;line-height:1.4;}
.vs-cell.them{color:var(--mute);border-right:1px solid var(--vsb);text-transform:uppercase;}
.vs-cell.us{color:var(--ink);text-transform:uppercase;font-weight:500;}
.vs-header{display:flex;border-bottom:1px solid var(--vsb);background:var(--tint);}
.vs-header .vs-cell{font-family:var(--goth);font-size:26px;letter-spacing:0.01em;text-transform:none;}
.vs-header .them{color:var(--mute);}
.vs-header .us{color:var(--ink);}
.feature-num{font-family:var(--mono);font-size:18px;letter-spacing:0.4em;color:var(--accent);text-transform:uppercase;margin-bottom:16px;}
.highlight-line{font-family:var(--serif);font-style:italic;font-weight:300;font-size:30px;line-height:1.4;
 color:var(--accent);margin-top:30px;padding-left:24px;border-left:2px solid var(--ink);}
.outro-content{align-items:center;text-align:center;justify-content:center;}
.outro-tagline{font-family:var(--serif);font-style:italic;font-weight:300;font-size:40px;line-height:1.4;color:var(--ink);margin:30px 0;max-width:780px;}
.outro-tagline strong{font-weight:400;font-style:normal;}
.outro-signature{font-family:var(--goth);font-size:56px;color:var(--ink);line-height:1;margin-top:50px;}
.outro-dm{font-family:var(--mono);font-size:16px;letter-spacing:0.4em;text-transform:uppercase;color:var(--accent);
 margin-top:30px;display:flex;align-items:center;gap:14px;justify-content:center;}
"""

SVG_DEFS = """
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="cross" viewBox="0 0 24 24"><path d="M12 1 L14 3 L14 9 L20 9 L22 11 L22 13 L20 15 L14 15 L14 21 L12 23 L10 21 L10 15 L4 15 L2 13 L2 11 L4 9 L10 9 L10 3 Z" fill="currentColor"/></symbol>
<symbol id="fleur" viewBox="0 0 24 24"><path d="M12 2 C12 6 9 8 9 11 C9 9 6 9 5 11 C7 11 7 13 9 14 L11 14 L11 18 L7 18 C5 18 4 17 3 18 C5 18 6 20 8 20 L11 20 L11 22 L13 22 L13 20 L16 20 C18 20 19 18 21 18 C20 17 19 18 17 18 L13 18 L13 14 L15 14 C17 13 17 11 19 11 C18 9 15 9 15 11 C15 8 12 6 12 2 Z" fill="currentColor"/></symbol>
<symbol id="flower" viewBox="0 0 24 24"><path d="M12 3 C13 6 15 7 17 6 C16 8 17 10 19 11 C17 12 16 14 17 16 C15 15 13 16 12 18 C11 16 9 15 7 16 C8 14 7 12 5 11 C7 10 8 8 7 6 C9 7 11 6 12 3 Z" fill="currentColor"/><circle cx="12" cy="11" r="2" fill="black"/></symbol>
<symbol id="arrow_right" viewBox="0 0 60 24"><path d="M0 12 L48 12 M36 4 L48 12 L36 20" fill="none" stroke="currentColor" stroke-width="2"/></symbol>
</defs></svg>
"""


def _head(num, total):
    return (
        '<div class="corner-mark tl">FC</div>'
        '<div class="corner-mark tr"><svg><use href="#cross"/></svg></div>'
        '<div class="corner-mark bl"><svg><use href="#fleur"/></svg></div>'
        '<div class="corner-mark br">est. 26</div>'
        '<div class="brand-banner"><svg><use href="#flower"/></svg> Flowers Chrome '
        '<svg><use href="#flower"/></svg></div>'
        f'<div class="slide-num">— 0{num} / 0{total} —</div>')


_SWIPE = '<div class="swipe-cue">Swipe <svg><use href="#arrow_right"/></svg></div>'


def _page(body, cls=""):
    return (f'<!DOCTYPE html><html><head><meta charset="UTF-8"><style>'
            f'{_fonts_css()}{CSS_BODY}</style></head><body>{SVG_DEFS}'
            f'<div class="post {cls}">{body}</div></body></html>')


# --------------------------------------------------------------------------- #
# Construction des slides à partir du dict `content`
# --------------------------------------------------------------------------- #
def _slide_hook(c, total):
    big = (f'<div class="big-price">{c["big"]}</div><div class="divider-line"></div>'
           if c.get("big") else "")
    sub = (f'<div style="font-family:var(--mono);font-size:14px;letter-spacing:0.4em;'
           f'text-transform:uppercase;color:var(--mute);margin-top:40px;">{c["hook_sub"]}</div>'
           if c.get("hook_sub") else "")
    return _page(_head(1, total) + f'''
  <div class="content">
    <div class="kicker">{c.get("kicker_hook","")}</div>
    {big}
    <div class="question-title" style="font-size:60px;">{c["hook_title"]}</div>
    {sub}
  </div>''' + _SWIPE, "slide-1")


def _slide_point(p, num, total, last=False):
    body = "".join(f"<p>{para}</p>" for para in p.get("body", []))
    block = ""
    if p.get("vs"):
        block = (f'<div class="vs-block"><div class="vs-header">'
                 f'<div class="vs-cell them">Ailleurs</div>'
                 f'<div class="vs-cell us">Flowers Chrome</div></div>'
                 f'<div class="vs-row"><div class="vs-cell them">{p["vs"]["them"]}</div>'
                 f'<div class="vs-cell us">{p["vs"]["us"]}</div></div></div>')
    bullets = ""
    if p.get("bullets"):
        items = "".join(
            f'<li><span class="mk">{b[0]}</span><span>{b[1]}</span></li>'
            if isinstance(b, (list, tuple))
            else f'<li><span class="mk">✓</span><span>{b}</span></li>'
            for b in p["bullets"])
        bullets = f'<ul class="bullets">{items}</ul>'
    body2 = ("".join(f"<p>{para}</p>" for para in p.get("body2", [])))
    body2 = f'<div class="body-text">{body2}</div>' if body2 else ""
    hi = f'<div class="highlight-line">{p["highlight"]}</div>' if p.get("highlight") else ""
    tcls = "slide-title smaller" if p.get("small_title") else "slide-title"
    return _page(_head(num, total) + f'''
  <div class="content">
    <div class="feature-num">{p.get("label","")}</div>
    <div class="{tcls}">{p["title"]}</div>
    <div class="body-text">{body}</div>
    {bullets}{block}{body2}{hi}
  </div>''' + ("" if last else _SWIPE))


def _slide_outro(c, total):
    return _page(_head(total, total) + f'''
  <div class="content outro-content">
    <div class="kicker">{c.get("outro_kicker","— la conclusion —")}</div>
    <div class="outro-tagline">{c["outro_tagline"]}</div>
    <div style="width:80px;height:1px;background:var(--ink);opacity:0.4;margin:40px auto;"></div>
    <div class="outro-signature">{c.get("outro_signature","Flowers Chrome")}<sup style="font-size:0.4em;vertical-align:super;margin-left:4px;">®</sup></div>
    <div class="outro-dm"><svg width="14" height="14" viewBox="0 0 10 10" style="fill:currentColor;"><path d="M5 0 L10 5 L5 10 L0 5 Z"/></svg> {c.get("outro_cta","DM ouverts")}</div>
  </div>''', "")


def build_slides_html(content):
    """Renvoie la liste des HTML (1 par slide) : hook + N points + outro."""
    points = content["points"]
    total = len(points) + 2
    htmls = [_slide_hook(content, total)]
    for i, p in enumerate(points):
        htmls.append(_slide_point(p, i + 2, total))
    htmls.append(_slide_outro(content, total))
    return htmls


def render_carousel(content, theme="dark", out_dir=".", prefix="carousel"):
    """Rend toutes les slides en PNG pour un coloris. Renvoie la liste des chemins."""
    if theme not in THEMES:
        raise ValueError(f"thème inconnu : {theme}")
    os.makedirs(out_dir, exist_ok=True)
    root_css = _root(THEMES[theme])
    htmls = build_slides_html(content)
    paths = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H})
        page = ctx.new_page()
        for i, html in enumerate(htmls, 1):
            # injecte le :root du thème juste après <style>
            html = html.replace("<style>", "<style>" + root_css, 1)
            page.set_content(html, wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=10000)
            page.wait_for_timeout(1200)
            out = os.path.join(out_dir, f"{prefix}_{theme}_{i:02d}.png")
            page.screenshot(path=out, clip={"x": 0, "y": 0, "width": W, "height": H})
            paths.append(out)
        browser.close()
    return paths


# --------------------------------------------------------------------------- #
# Contenu de référence (pour le test des 3 coloris)
# --------------------------------------------------------------------------- #
REFERENCE_CONTENT = {
    "kicker_hook": "— la vraie valeur —",
    "big": "194€",
    "hook_title": "C'est cher<br>pour une montre ?",
    "hook_sub": "— regarde ce qu'il y a dedans —",
    "points": [
        {"label": "— 01 · le verre —", "title": "Saphir.<br>Pas minéral.",
         "body": ["À ce prix, la plupart des montres ont un verre minéral qui se raye au moindre contact."],
         "vs": {"them": "Verre minéral<br>rayé en 6 mois", "us": "Verre saphir<br>anti-rayures"},
         "body2": ["Le saphir, c'est ce qu'on trouve sur les montres à <em>plusieurs milliers d'euros</em>."]},
        {"label": "— 02 · le mouvement —", "title": "Un moteur<br><em>japonais.</em>",
         "body": ["Le cœur de la montre, c'est son mouvement. Les miens sont des mécanismes <strong>japonais reconnus</strong> — fiables, réparables, faits pour durer."],
         "vs": {"them": "Quartz<br>bas de gamme", "us": "Mouvement<br>japonais fiable"}},
        {"label": "— 03 · l'assemblage —", "title": "Montée à la main.<br>Pas à la chaîne.",
         "small_title": True,
         "body": ["Chaque pièce est assemblée et contrôlée une par une. Boîtier acier, finitions soignées, lunette sertie.",
                  "Et surtout : chaque modèle existe en <strong>quantité très limitée</strong>. Souvent une seule pièce."],
         "highlight": "Tu ne croiseras pas trois personnes avec la même au poignet."},
    ],
    "outro_tagline": "Le prix d'une montre de centre commercial.<br><br>Sauf que <strong>celle-là</strong>,<br>tu la gardes des années.",
    "outro_signature": "Flowers Chrome",
    "outro_cta": "DM ouverts — commandes &amp; projets perso",
}
