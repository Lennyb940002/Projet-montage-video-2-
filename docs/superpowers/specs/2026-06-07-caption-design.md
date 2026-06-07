# Description + Hashtags — Design

**Date :** 2026-06-07
**Statut :** Design validé
**Contexte :** Nouvelle fonctionnalité de l'app AutoMontage. Génère une description TikTok/Reels + hashtags à partir de la transcription, **en local** (sans IA/clé API), affichée et éditable dans l'app.

## Objectif

Au dépôt de l'audio, produire automatiquement une **description prête à coller** : accroche + 2-3 bénéfices + CTA + hashtags. Affichée dans un panneau éditable avec boutons **Copier** et **Régénérer**.

## Décisions validées
- Génération **locale / templates** (pas d'IA, pas de clé).
- Structure : **accroche + 2-3 bénéfices + CTA + hashtags**.
- Hashtags : **set par défaut éditable** + **marque détectée** ajoutée (#seiko, #rolex…).
- Livraison : **dans l'app uniquement** (panneau éditable + Copier), rien sur le disque.

## Génération (module `backend/pipeline/caption.py`)

`generate_caption(text) -> {description, hashtags, full}` où :
- **Accroche** : 1ʳᵉ phrase du texte.
- **Bénéfices** : jusqu'à 3 phrases du texte contenant un mot « vendeur »
  (`prix, qualité, livraison, saphir, acier, 24h, €, garantie, automatique, mouvement…`),
  hors accroche et hors CTA, préfixées « ✅ ». Si < 1 trouvée → liste par défaut (config).
- **CTA** : 1ʳᵉ phrase contenant un verbe d'appel (`écris, commente, commande, abonne, suis, clique`)
  sinon CTA par défaut (config : « Écris-moi en commentaire 👇 »).
- **Hashtags** : `BASE_HASHTAGS` (config, éditable) + tag de chaque **marque détectée**
  (map `BRAND_TAGS`, ex. seiko→#seiko), dédoublonnés, max ~12.
- **full** = description + ligne vide + hashtags joints par espace.

Réutilise la détection de marques de `sfx_plan` (WATCH_BRANDS) pour rester cohérent.

## API
- `/load` (existant) renvoie en plus `caption` (généré depuis la transcription initiale).
- Nouveau `POST /caption {text}` → `{description, hashtags, full}` (régénération après édition).

## Réglages (`config.py`)
`BASE_HASHTAGS` (liste), `DEFAULT_BENEFITS` (liste), `DEFAULT_CTA` (str), `BRAND_TAGS` (dict marque→#tag), `BENEFIT_KEYWORDS` (liste).

## UI (frontend)
- Panneau droit : **onglets « Transcription | Description »**.
- Onglet Description : `<textarea>` rempli avec `caption.full` (éditable) + boutons **Copier** (presse-papiers) et **Régénérer** (appelle `/caption` avec le texte courant de la transcription).
- Au dépôt de l'audio, l'onglet Description est pré-rempli.

## Erreurs & tests
- **Erreurs** : texte vide → description minimale (juste hashtags) sans planter.
- **Tests** : `generate_caption` → accroche = 1ʳᵉ phrase ; ajoute #seiko si « Seiko » présent ; CTA détecté ou défaut ; bénéfices préfixés ✅ ; hashtags dédoublonnés.

## Hors périmètre
Le sous-système **B** (poster/programmer sur TikTok & Instagram) fera l'objet d'un spec séparé.
