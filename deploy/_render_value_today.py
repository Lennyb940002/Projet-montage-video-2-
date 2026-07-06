"""Rend le carrousel valeur du jour (texte copywriter) — coloris light."""
import os
from backend.posts.carousel import render_carousel

CONTENT = {
    "kicker_hook": "la plupart regardent le logo",
    "hook_title": "Comment reconnaître<br>une montre<br>de qualité ?",
    "hook_sub": "— les passionnés regardent ces 3 détails —",
    "points": [
        {"label": "— 01 · le verre —", "title": "Le verre.",
         "body": ["Une montre de qualité protège son cadran durablement."],
         "vs": {"them": "Verre minéral<br>se raye plus vite",
                "us": "Verre saphir<br>anti-rayures · premium"},
         "body2": ["Le verre est souvent le premier indice."]},
        {"label": "— 02 · le mouvement —", "title": "Le mouvement.",
         "body": ["C'est le cœur de la montre. Une montre peut être belle dehors… "
                  "et décevoir dedans."],
         "bullets": ["Fiabilité", "Précision", "Longévité"]},
        {"label": "— 03 · les finitions —", "title": "Les finitions.",
         "small_title": True,
         "body": ["Regarde les détails :"],
         "bullets": ["Alignement des index", "Finition du bracelet",
                     "Qualité du cadran", "Travail des aiguilles"],
         "highlight": "C'est souvent là que la différence se voit."},
    ],
    "outro_tagline": "Une belle montre ne se résume pas à son prix.<br><br>"
                     "Les <strong>détails</strong> font toute la différence.",
    "outro_signature": "Flowers Chrome",
    "outro_cta": "DM « MONTRE » pour les modèles dispo",
}

if __name__ == "__main__":
    out = os.path.join(os.path.expanduser("~"), "carousel_value_today")
    paths = render_carousel(CONTENT, theme="light", out_dir=out, prefix="val")
    print("RENDERED", len(paths), "->", out)
    for p in paths:
        print(p)
