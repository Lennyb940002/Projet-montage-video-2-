"""Format 'story question texte' : une story 1080x1920 sombre avec une question
d'engagement (incite à répondre en DM/commentaire). Rendu PIL. Aucune dépendance
lourde. Le sticker 'question' natif d'Instagram (interactif) reste à ajouter à la
main dans l'app si voulu ; ici c'est une image texte avec appel à répondre."""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920

QUESTIONS = [
    "Ta montre en dit quoi sur toi ?",
    "Cadran noir ou cadran bleu ?",
    "Acier ou or ?",
    "Discrète ou qui se remarque ?",
    "C'est quoi ta montre de rêve ?",
    "Tu mettrais combien dans une montre ?",
    "Une montre pour un premier rendez-vous ?",
    "Tu regardes l'heure ou le style ?",
    "GMT, Daytona ou Nautilus ?",
    "Ta montre, tu la portes tous les jours ?",
    "Or rose : classe ou trop voyant ?",
    "Quelle couleur au poignet cet été ?",
    "Automatique ou ça t'est égal ?",
    "La montre fait-elle l'homme ?",
]


def _font(size):
    for p in (r"C:\Windows\Fonts\Montserrat-Bold.ttf",
              r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_story_question(question, out):
    img = Image.new("RGB", (W, H), (11, 11, 13))
    d = ImageDraw.Draw(img)
    for y in range(H):                       # léger dégradé vertical
        c = int(9 + 14 * (y / H))
        d.line([(0, y), (W, y)], fill=(c, c, c + 3))

    lf = _font(44)
    lab = "LA QUESTION DU JOUR"
    d.text(((W - d.textlength(lab, font=lf)) // 2, 300), lab, font=lf, fill=(150, 150, 162))

    qf = _font(104)
    lines = _wrap(d, question, qf, W - 200)
    lh = 128
    y = (H - len(lines) * lh) // 2 - 40
    for ln in lines:
        d.text(((W - d.textlength(ln, font=qf)) // 2, y), ln, font=qf, fill=(255, 255, 255))
        y += lh

    # pastille CTA en bas
    bf = _font(50)
    cta = "Réponds en DM"
    tw = d.textlength(cta, font=bf)
    bx, by, pad = (W - tw) // 2, H - 470, 34
    d.rounded_rectangle([bx - pad, by - pad, bx + tw + pad, by + 74 + pad],
                        radius=40, fill=(94, 84, 242))
    d.text((bx, by), cta, font=bf, fill=(255, 255, 255))
    img.save(out)
    return out
