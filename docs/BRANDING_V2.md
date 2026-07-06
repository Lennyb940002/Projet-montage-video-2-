# FLOWERS CHROME — BRANDING V2 (Décision V1, révisable)

> **Statut : Décision de marque V1 — validée le 2026-07-01, révisable par la donnée.**
> Gouverné par [STRATEGIE_CANON.md](STRATEGIE_CANON.md). Toute production (captions, hooks, stories, bio, DM, visuels) doit s'y conformer. Les générateurs visuels ne sont PAS encore modifiés : en attente de validation de l'emblème + du système graphique.

## 1. Identité psychologique — L'ASCENDANT MAGNÉTIQUE
La marque s'adresse à **l'homme qui est en train de monter, de se construire, de prendre sa place**. Il ne cherche pas à paraître riche ; il veut dégager **ambition, maîtrise, présence, une part de mystère**, et le sentiment qu'il avance pendant que les autres stagnent.
> Ressenti cible : **« Cette montre ressemble à l'homme que je suis en train de devenir. »**

## 2. Signatures verbales
- **Baseline principale (à tester) :** « **Porte ce que tu deviens.** » *(exprime une transformation, pas une qualité sociale)*
- **Baseline secondaire (commerciale) :** « Ta première vraie montre automatique. »

## 3. Direction artistique — Nocturne réchauffé + signature Chrome
- **Nocturne** apporte : désir, profondeur, masculinité, confiance, univers premium.
- **Chrome** apporte : différenciation, modernité, cohérence avec le nom, signature reconnaissable.
- Le chrome est un **accent distinctif**, jamais envahissant (pas de froideur / gadget futuriste).

### Palette V1
`#070707` noir profond · `#18191B` graphite · `#C4C8CC` chrome argent · `#F2F3F4` blanc froid · `#C99645` ambre chaud · accent spectral bleu-violet **très discret** (uniquement dans certains reflets).

### Lumière
Fond majoritairement noir · lumière chaude rasante sur montre/poignet · reflets chrome nets sur les contours · fort espace négatif. **Jamais** de lumière plate, jamais d'esthétique « boutique AliExpress », jamais de saturation holographique.

### Typographie
Serif élégante pour les accroches de marque · sans-serif moderne et nette pour l'info · peu de texte · capitales espacées pour les titres. **Pas** de typo massive streetwear, **pas** de faux codes « old money ».

### Ton
Calme, sûr de lui, ambitieux — « quelqu'un qui sait où il va ». **Jamais** arrogant, « sigma » caricatural, agressif, trop luxueux, ni techniquement prétentieux.

## 4. Emblème
- **Emblème principal V1 validé le 2026-07-01.** Le monogramme FC chrome sur fond noir est la **photo de profil officielle** de Flowers Chrome. Décision révisable uniquement sur données d'usage ou problème de lisibilité réel. Itérations arrêtées.
- **Motif secondaire = Variante B** (fleur chromée — watermark Reels, packaging, accents).
- Variante C (sceau) : packaging uniquement (clash avec le crop rond IG).

## 5. Système visuel des contenus (règles exécutables)
Fond noir ≥70 % · lumière chaude rasante + reflets chrome · plan macro, une montre héros décentrée · texte en tiers haut/bas jamais sur le cadran · max 5-7 mots / 2 blocs · serif capitales espacées (accroche) + sans-serif (info) · animation sur le bloc + lumière qui balaye · logo coin ~6-8 % · chrome/spectral en accent seulement. **Interdits :** lumière plate, fond boutique, watermark d'app, emojis dans les Reels premium, texte sur le cadran.

## 6. Ligne de modèles (fin de « Seiko Daytona »)
FC Aurora (or rose) · FC Nocturne (saphir) · FC Braise (ruby) · FC Éclipse (silver) · FC Méridien (GMT). *(Appliqué dans `backend/config.py`.)*

## 7. Lexique de marque (garde-fou, cf. Canon V1 + `backend/silent/canon.py`)
- ❌ Interdit : mod, SKX, parts, build, DIY, jargon technique/revente, « Seiko Daytona/Datejust ».
- ✅ Autorisé : « montre automatique Flowers Chrome », « assemblée & contrôlée à la main », « mouvement automatique fiable », « saphir », « pièce », « cadran ».
- On vend le **ressenti / le look / l'identité**, jamais la fiche technique.

## 8. Bio & CTA V1
Bio V1 retenue (~127 caractères, sous la limite IG de 150) :
> Porte ce que tu deviens.
> Montres automatiques assemblées et contrôlées à la main.
> DM « CHOIX » — je t'aide à trouver la tienne.

CTA de marque : conseil gratuit à faible coût d'action (« Écris CHOIX »).
> ⚠️ **Sous réserve :** « assemblées et contrôlées à la main » doit correspondre **exactement** à la réalité opérationnelle. Aucune promesse non vérifiée (prix, saphir, retours, livraison, avis) n'est présentée comme validée tant qu'elle n'est pas confirmée.

## 8bis. Captions V2 — Frozen V1 (2026-07-02)
Le système de captions (`backend/silent/captions_v2.py` + contexte éditorial par concept dans `deploy/test_batch_v2.json`) est **figé**. « Frozen » ≠ définitif : **aucune modification avant les premières données réelles**, sauf erreur factuelle ou juridique. Batch 24 = Miroir 4 · Choix forcé 4 · Projection 3 · Bascule 3 · **Révélation 4** · Conseil 4 · **Preuve 2 (bloquées, matière réelle requise)**. `#horlogerie` en whitelist mais non utilisé par le batch. CTA save/share séparés, voix je/tu, sans emoji.

## 8ter. Stories V2 — Frozen V1 (2026-07-03)
Système visuel stories **gelé** : vrai monogramme (`assets/avatar/`, pack + transparent, tracé `fc_avatar_v1` dans chaque manifeste, **aucun fallback** — master absent = `blocked_missing_brand_asset`) · **Cadre Nocturne obligatoire** pour les 13 photos actuelles (`presentation_mode: nocturne_frame`, full-bleed conservé hors mix, retour explicite par asset) · monogramme unique coin bas droit 80px (marges 64/320) · photos héros choisies explicitement (`backend/posts/preferred_assets.json`) · safe-zones + collisions vérifiées par test navigateur. **En attente uniquement : faits commerciaux (`FACTS_TO_CONFIRM.md`) + assets réels bloqués (avis, contrôle qualité, wrist-shots).** Publication et cadence non branchées.

## 9. Highlights V1
MODÈLES (désir) · CHOISIR (→ DM) · AVIS (preuve) · QUALITÉ (**confiance** : montre le contrôle, les détails, la préparation, la vérification, le soin avant expédition — **jamais** une fiche technique) · LIVRAISON (risque perçu) · FAQ (peurs). Icônes chrome ligne fine sur noir. *Contenu complet écrit après validation de l'emblème + bio.*
