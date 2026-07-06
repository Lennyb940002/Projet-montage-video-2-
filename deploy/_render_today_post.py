"""One-shot : rend un carrousel valeur (contenu écrit à la main) en coloris dark."""
import os
from backend.posts.carousel import render_carousel

CONTENT = {
    "kicker_hook": "— le grand débat —",
    "big": "VS",
    "hook_title": "Automatique<br>ou quartz ?",
    "hook_sub": "— ce que personne ne t'explique —",
    "points": [
        {"label": "— 01 · l'énergie —", "title": "D'où vient<br>le mouvement ?",
         "body": ["Le quartz avance grâce à une <strong>pile</strong>. L'automatique, lui, "
                  "se remonte tout seul avec <strong>les mouvements de ton poignet</strong>. "
                  "Aucune pile."],
         "vs": {"them": "Quartz<br>pile à changer", "us": "Automatique<br>remontée au poignet"},
         "body2": ["Tant que tu la portes, elle vit. <em>Sans rien faire.</em>"]},
        {"label": "— 02 · le ressenti —", "title": "La trotteuse<br>qui glisse.",
         "body": ["Regarde l'aiguille des secondes. Le quartz fait <strong>tic… tac…</strong> "
                  "saccadé. L'automatique <strong>balaie</strong> le cadran d'un geste continu."],
         "vs": {"them": "Quartz<br>secousse sèche", "us": "Automatique<br>balayage fluide"}},
        {"label": "— 03 · la durée —", "title": "Faite pour<br>te survivre.",
         "small_title": True,
         "body": ["Une pile finit par mourir. Un mouvement automatique, lui, se <strong>répare</strong>, "
                  "s'entretient et se <strong>transmet</strong>.",
                  "C'est une mécanique vivante, pas un composant jetable."],
         "highlight": "Une pile, ça se jette. Un mouvement, ça se transmet."},
    ],
    "outro_kicker": "— la conclusion —",
    "outro_tagline": "Le quartz donne l'heure.<br><br>L'<strong>automatique</strong>, lui, "
                     "raconte quelque chose. C'est pour ça qu'on a choisi le mouvement "
                     "<strong>japonais automatique</strong>.",
    "outro_signature": "Flowers Chrome",
    "outro_cta": "DM ouverts — commandes &amp; projets perso",
}

CAPTION = (
    "⚙️ Automatique ou quartz : le débat qui revient tout le temps.\n\n"
    "La vraie différence n'est pas le prix — c'est ce qu'il se passe à l'intérieur. "
    "Le quartz fonctionne à la pile : précis, pratique, mais jetable. L'automatique se "
    "remonte avec les mouvements de ton poignet : pas de pile, une trotteuse qui balaie "
    "le cadran, et un mécanisme qui se répare et se transmet.\n\n"
    "Chez Flowers Chrome, chaque pièce embarque un mouvement automatique japonais reconnu "
    "— fiable, réparable, fait pour durer des années. Une montre qui vit tant que tu la portes.\n\n"
    "📩 Une question, un projet sur-mesure, une commande → DM ouverts.\n\n"
    "#seikomod #montreautomatique #montrehomme #horlogerie #watchesofinstagram #flowerschrome"
)

if __name__ == "__main__":
    out = os.path.join(os.path.expanduser("~"), "value_post_today")
    paths = render_carousel(CONTENT, theme="dark", out_dir=out, prefix="post")
    print("RENDERED:", len(paths), "slides ->", out)
    for p in paths:
        print(p)
