# -*- coding: utf-8 -*-
"""Banque de sujets de videos avec voix off (Gemini TTS via make_voice.py).
Positionnement : montre PERSONNALISEE creee sur mesure. Honnete (jamais marque
de luxe / Seiko mod / haute horlogerie). Objectif : DM entrants.

Chaque entree : hook (3 premieres sec) + script VO complet + CTA + duree cible.
Les scripts sont ecrits pour etre LUS (voix off), pas affiches en pave.
"""

SCRIPTS = {

    # ---- Series signature "Ton idee, ta montre" ----
    "ton_idee": {
        "hook": "Il m'a envoye une photo. Voila ce que j'en ai fait.",
        "vo": ("Il m'a envoye une photo, juste une idee en tete. "
               "On a choisi ensemble le boitier, la couleur du cadran, les aiguilles, le bracelet. "
               "J'ai selectionne les pieces compatibles, je l'ai assemblee, reglee, testee. "
               "Resultat : une montre qui n'existe qu'en un seul exemplaire. La sienne. "
               "Toi aussi tu as une idee ? Envoie-la moi en message, je te dis si c'est faisable."),
        "cta": "DM PROJET", "dur": 18,
    },

    "faisable": {
        "hook": "Envoie-moi ta montre de reve. Je te dis si je peux la creer.",
        "vo": ("Envoie-moi une photo de la montre que tu as en tete. "
               "Une inspiration, une couleur, un style, meme flou. "
               "Je regarde, et je te dis franchement : realisable ou pas, et a quel prix. "
               "Pas de catalogue impose : on part de ton idee a toi. "
               "Alors, c'est quoi ta montre parfaite ? Ecris-moi en message."),
        "cta": "Envoie ta photo en DM", "dur": 16,
    },

    # ---- Config / budget ----
    "budget_200": {
        "hook": "T'as 200 euros. Voila la montre que je peux te creer.",
        "vo": ("T'as un budget de deux cents euros. "
               "Avec ca, on choisit ton boitier, un cadran a ta couleur, le bracelet qui va avec. "
               "Une piece assemblee et reglee, faite pour toi, que personne d'autre n'aura. "
               "Sobre ou plus marquee, c'est toi qui decides. "
               "Dis-moi ton budget et ton style, je te propose ta config aujourd'hui."),
        "cta": "DM DEVIS", "dur": 17,
    },

    "trois_configs": {
        "hook": "Le meme boitier. Trois hommes completement differents.",
        "vo": ("Meme point de depart : un seul boitier. "
               "Premiere version, sobre et discrete, pour le mec classe. "
               "Deuxieme, cadran plus fort, pour celui qui aime qu'on remarque. "
               "Troisieme, esprit vintage, pour le connaisseur. "
               "Trois personnalites, trois montres uniques. Laquelle est la tienne ?"),
        "cta": "DM MOI", "dur": 16,
    },

    # ---- Pedagogie / autorite (VO brille ici) ----
    "erreur": {
        "hook": "Neuf personnes sur dix se plantent sur ce detail.",
        "vo": ("La plupart des gens choisissent leur cadran et leur bracelet separement. "
               "Resultat : deux belles pieces, mais qui jurent ensemble. "
               "Mon boulot, c'est justement d'eviter ca : "
               "harmoniser les couleurs, les proportions, les finitions, pour que tout tienne. "
               "Tu veux creer ta montre sans te tromper ? Ecris-moi, je t'accompagne."),
        "cta": "DM AIDE", "dur": 17,
    },

    "processus": {
        "hook": "Comment on cree ta montre, etape par etape.",
        "vo": ("Etape une : tu m'envoies ton idee. "
               "Etape deux : je te propose une configuration compatible, boitier, cadran, aiguilles, bracelet. "
               "Etape trois : je selectionne les pieces et je l'assemble a la main. "
               "Etape quatre : je la regle, je la teste, et elle part chez toi. "
               "Ton idee, ta montre. On commence quand tu veux, en message."),
        "cta": "DM PROJET", "dur": 18,
    },

    # ---- Identite / projection ----
    "style": {
        "hook": "Dis-moi comment tu t'habilles. Je te cree ta montre.",
        "vo": ("Total black et streetwear ? On part sur un boitier sombre, cadran epure. "
               "Plutot classique, chemise ? Un cadran clair, un bracelet sobre. "
               "Le but, c'est que ta montre te ressemble, pas qu'elle ressemble a celle du voisin. "
               "Decris-moi ton style en deux mots, je te montre ce que je peux creer pour toi."),
        "cta": "DM STYLE", "dur": 16,
    },

    "unique": {
        "hook": "Tout le monde porte la meme. Toi, non.",
        "vo": ("Les montres qu'on voit partout, tout le monde les a. "
               "Une montre creee sur mesure, elle n'existe qu'une fois. "
               "Ta couleur, tes finitions, ton idee, assemblees rien que pour toi. "
               "Le vrai luxe aujourd'hui, ce n'est pas le logo, c'est d'avoir quelque chose que personne d'autre n'a. "
               "Envie de la tienne ? Ecris-moi."),
        "cta": "DM MOI", "dur": 16,
    },

    "cadeau": {
        "hook": "Le cadeau qu'il n'oubliera jamais : la sienne.",
        "vo": ("Offrir une montre, c'est bien. "
               "Offrir LA sienne, creee selon ses gouts a lui, c'est autre chose. "
               "Tu me donnes son style, sa couleur preferee, ton budget. "
               "Je m'occupe du reste : une piece unique, assemblee et prete a offrir. "
               "Un cadeau qu'il gardera. Ecris-moi, on la cree ensemble."),
        "cta": "DM CADEAU", "dur": 17,
    },

    # ---- Preuve / coulisses ----
    "atelier": {
        "hook": "Une commande, du message a ton poignet.",
        "vo": ("Tout commence par un message et une idee. "
               "Je selectionne les pieces compatibles, je monte le mouvement, le cadran, les aiguilles, le bracelet. "
               "Je regle, je controle, je teste. "
               "Et quelques jours plus tard, elle est a ton poignet. "
               "Une montre personnalisee, faite pour une seule personne. Toi."),
        "cta": "DM PROJET", "dur": 17,
    },
}


def get(name):
    return SCRIPTS[name]


if __name__ == "__main__":
    print(f"{len(SCRIPTS)} sujets VO disponibles :")
    for k, v in SCRIPTS.items():
        print(f"  - {k:14s} ~{v['dur']}s  | hook: {v['hook']}")
