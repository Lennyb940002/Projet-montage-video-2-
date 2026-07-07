# Format « Sélection rafale » (reverse-engineering LMDLS) — spec de réplication

> Analyse de 7 vidéos TikTok du compte @lemediadelasape (LMDLS, "Le Média de la Sape"),
> format sélection de vêtements. Analysé le 2026-07-07 avec ffprobe/ffmpeg
> (détection de cuts scene>0.25, contact sheets, YDIF, volumedetect).
> Objectif : règles chiffrées pour répliquer et automatiser ce format pour Flowers Chrome.

## Corpus analysé

| id | fichier (Downloads) | durée | structure mesurée |
|----|---------------------|-------|-------------------|
| v1 | « C'est lequel ton préféré ✨ » | 60,4 s | hook 7,5 s puis ~5 produits × ~10 s (multi-marques : Pepe Studio, Stussy, Forever Vacation, Davril Supply, Amoses, Noclout) |
| v2 | « Incroyable #outfitideas » | 12,5 s | hook 8,3 s + 5 plans + outro |
| v3 | « Incroyable 😍 » | 17,1 s | hook 10,0 s + 7 plans (APARE.EU) |
| v4 | « Incroyable 😍 #fyp » | 12,6 s | hook 6,5 s + 8 plans (Brouillon.eu) + outro |
| v5 | « 🍯 (1) » | 17,5 s | hook 9,9 s + 7 plans (APARE.EU) + outro |
| v6 | « 🍯 » | 12,0 s | hook 7,9 s + 6 plans (Triple Sphere) + outro |
| v7 | « 🤯 » | 18,7 s | hook 9,9 s + 9 plans (APARE.EU) + outro |

Tous : 576×1024 (source TikTok compressée — produire en 1080×1920), 30 fps, AAC 44,1 kHz stéréo.

## Structure en 3 actes (invariante sur les 7 vidéos)

```
[ HOOK photo fixe + texte progressif ]  [ RAFALE produits cuts secs ]  [ OUTRO logo ]
0 ──────────────────────────── 55-65% ───────────────────────── 95% ────────── 100%
   musique build-up (~-23 dB)      drop + beat (~-17,5 dB)           fin sèche
```

### Acte 1 — HOOK (6,5 à 10 s)

- **1 photo fixe unique** (YDIF ≈ 0,05 mesuré = zéro motion, pas même de zoom).
- Sujet : personne en outfit streetwear complet, **visage jamais mis en avant**
  (coupé au cadrage, tête baissée, lunettes, regard ailleurs) → focus vêtements.
- Décor urbain fort et coloré : voiture ancienne, vélo, devanture record store,
  container jaune, trottoir. La photo doit « claquer » seule.
- **Texte centré, empilé, apparition ligne par ligne toutes les ~0,8 s**
  (mesuré : 1 ligne / 2 frames à 2,5 fps). La pile complète reste affichée
  ~1,5–2 s avant la rafale.
- Formule du texte (5–7 lignes de 1–2 mots) :
  `Les / [meilleurs|adjectif] / [produit] / [qualificatif hype] / [contexte temporel] / part N`
  Exemples relevés :
  - « Les / meilleurs / maillots / à avoir / absolument / **cet été** / part 6 »
  - « Les / t-shirts / incroyables / que presque / personne / ne connaît / part 2 »
  - « Les / t-shirts / sous-cotés / que presque / personne / ne connaît / part 1 »
  - v1 : « Les / meilleurs / pulls / pour passer / l'hiver / Choisis ton préféré / part 1 »
- Style texte : police bold type TikTok (Proxima Nova-like), ombre portée noire,
  **alternance blanc / jaune-orangé** — le jaune sur les mots porteurs
  (produit, qualificatif, période). Le dernier mot-clé peut être un
  **badge rouge arrondi** (« cet été ») ou jaune + emoji. « part N » en petit corps blanc.

### Acte 2 — RAFALE produits (jusqu'à ~1 s de la fin)

- **5 à 9 plans de 0,6 à 1,3 s**, cuts secs, aucune transition.
  Intervalles mesurés v2 : 0,63–0,67 s ; v3/v5/v7 : 1,0–1,3 s ; v4 : 0,67–0,75 s.
  Régularité forte → calés sur le beat de la musique.
- Types de plans qui reviennent (piocher 5–9 dans cette liste, varier l'ordre) :
  1. flat lay au sol (produit posé, sol béton/pavés/texture)
  2. flat lay avec **pieds du photographe visibles en POV** (très identitaire)
  3. dos du vêtement (print principal)
  4. gros plan matière / print / broderie
  5. étiquette-tag tenue à la main
  6. porté en situation (photo lifestyle)
  7. variantes de coloris côte à côte
- **Caption fixe en haut** (~12–15 % de la hauteur), identique sur tous les plans
  d'un même produit : ligne 1 = **marque/site en jaune-orangé bold**
  (« APARE.EU », « Brouillon.eu », « SIDE ARTS », « Triple Sphere ») ;
  ligne 2 = nom produit en blanc (« Apogée » t-shirt). Ombre noire.
- Variante 60 s (v1) : plusieurs produits enchaînés, ~10 s et 4–8 plans chacun,
  la caption change à chaque produit. Hook = « Choisis ton préféré »
  → CTA commentaire implicite.

### Acte 3 — OUTRO (~1 s)

- Carte pleine page **jaune fluo** (≈ #D6F320) avec logo noir centré (« LMDLS »).
- Coupe sèche, pas de fade.

## Audio (mesuré)

- Une seule musique sur toute la vidéo, **build-up pendant le hook puis drop
  au premier cut produit** : mean_volume intro ≈ −23 dB → rafale ≈ −17,5 dB
  (+5 à +6 dB systématiques sur v2/v4/v7).
- Le beat de la rafale = la grille de cuts. Si BPM connu : shot_dur = 1 ou 2 beats.

## Pourquoi ça marche (à préserver dans la réplique)

1. Photo fixe + texte qui se révèle = rétention sans effort de prod.
2. Promesse liste (« les meilleurs X ») + « part N » = format série, repassage profil.
3. Drop musical synchronisé au premier produit = récompense.
4. Rafale rapide = re-watch (on n'a pas le temps de tout voir).
5. Caption marque/nom = valeur sauvegardable (le viewer screenshot/enregistre).

## Adaptation Flowers Chrome (paramètres proposés)

- **Inputs par vidéo** : 1 photo hook lifestyle (montre au poignet, outfit, décor urbain),
  1 liste de 5–9 assets produit (photos/clips montres : flat lay, macro cadran,
  bracelet, au poignet, boîte), textes {produit, qualificatif, période}, numéro de part.
- **Formule hook** (banque à créer dans `backend/silent/banks/`) :
  « Les / montres / [sous-cotées|incroyables|à avoir] / [que presque personne ne connaît|absolument] / [cet été|en 2026] / part N »
- **Paramètres de rendu** :
  - `t_intro = n_lignes × reveal_interval + hold` avec `reveal_interval = 0,8 s`, `hold = 1,5–2 s`
  - `shot_dur ∈ [0,6 ; 1,3] s` (constant au sein d'une vidéo, tiré par la policy ; beat-sync si BPM)
  - `n_shots ∈ [5 ; 9]` ; `outro = 1,0 s` carte marque Flowers Chrome
  - musique : gain −6 dB sur l'intro, plein volume à `t_intro` (ou track avec vrai drop)
  - sortie 1080×1920@30, cuts secs, zéro transition, zéro motion sur le hook
- **Mapping architecture** (conventions repo) : la **policy** décide formule, n_shots,
  shot_dur, ordre des types de plans → `VideoRecipe` avec labels → renderer purement
  exécutif (nouveau format dans `backend/silent/` à côté de `special_render.py`).
  Aucun texte hardcodé dans le renderer.
- Sérialiser dès le départ : « part 1 », « part 2 »… même formule, même outro.

## Limites de l'analyse

- Musiques non identifiées (pas de Shazam) ; BPM non extrait.
- Le texte exact des captions est lu sur frames compressées 576×1024 (fiable mais
  vérifier les accents avant de copier un style).
- Fichiers sources conservés dans Downloads ; frames d'analyse dans le scratchpad session.

---

# Implémentation & VALIDATION (2026-07-07)

**Statut : VALIDÉ.** 3 vidéos montres produites, itérées avec le owner et approuvées
(« c'est parfait »), envoyées sur Telegram. Ci-dessous l'état réellement construit
(qui affine certains paramètres proposés ci-dessus après retour du owner).

## Ce qui a été construit

- **Moteur** : [`deploy/rafale_engine.py`](../../../deploy/rafale_engine.py) — rendu 100 % ffmpeg,
  `drawtext` avec **fontfile TTF explicite** (`C:\Windows\Fonts\ariblk.ttf`) car pas de
  fontconfig sur ce PC. Segments (intro + clips) encodés identiques (libx264 crf 18,
  1080×1920, 30 fps) puis concaténés ; audio **loudnorm -16 LUFS**, fade out, AAC 48 kHz.
- **Analyse musique** : [`deploy/analyze_music.py`](../../../deploy/analyze_music.py) — yt-dlp
  (`player_client=android_music` pour contourner 403/DRM) → wav → librosa `onset_strength`
  + `beat_track`. Fenêtre **16 s la plus percussive**, snap sur **beat fort**, beats relatifs.
- **Driver / preset** : [`deploy/make_3_rafale.py`](../../../deploy/make_3_rafale.py) — mappe les
  beats sur les apparitions de mots et les coupes ; définit les 3 recettes.
- **Assets persistants** : `Downloads/rafale_out/_assets/` (segments musique 16 s + `analysis.json`) ;
  clips produit `Downloads/noTube/*.mp4` ; sortie `Downloads/rafale_out/`.

## Réglages VALIDÉS (écrasent les propositions initiales)

| Paramètre | Proposé (analyse) | **Validé (owner)** |
|---|---|---|
| Durée | 12-18 s | **15 s** |
| Motion hook | zéro | **zéro** (confirmé : le zoom d'intro a été retiré) |
| Filtre photo | — | **aucun** (overlay sombre retiré) |
| Taille texte | bold | **énorme, chaque mot remplit la largeur** (auto-fit) |
| Apparition mot | ligne / 0,8 s | **1 mot / beat, INSTANTANÉE** (pas de fondu/slide : le slide 0,18 s cassait le ressenti rythme) |
| Départ | drop au 1er produit | **1er mot déjà calé sur un beat fort** (t=0) |
| Pause avant rafale | 1,5-2 s | **1,2-2 s, puis montre sur un temps fort** |
| Nb produits | 5-9 rapides | **2-3, ~3 s chacun** (owner veut qu'ils restent) |
| Caption produit | marque + nom | **nom du modèle seul, pas de prix** |
| Couleurs | blanc/jaune-orangé | **blanc + `#FFD400`**, contour noir épais |
| Outro carte marque | 1 s | **non implémentée** (peut être ajoutée) |

## Reproduire

```bash
python deploy/make_3_rafale.py all      # -> Downloads/rafale_out/rafale_{1,2,3}_*.mp4
# env : RAFALE_ASSETS, RAFALE_NOTUBE, RAFALE_OUT, RAFALE_FONT
```

Les 3 vidéos de référence : V1 Diva / V2 Milkshake / V3 DAME UN GRR ; intros
`intro_02, intro_09, intro_16` ; hooks « incroyables », « sous-cotées », « meilleures … cet été ».

## Itérations restées ouvertes

- Entrée montre sur un **downbeat de mesure** (4 temps) plutôt que temps pair, si besoin.
- **Nudge global** des beats si décalage résiduel perçu à l'oreille (owner valide au son).
- SFX whoosh sur les coupes (dossier `SFX/` vide).
- Génération de **lots** (rotation hooks × intros × sons) ; outro carte Flowers Chrome.
- Portage PC de bureau : le moteur résout ffmpeg 8.1.1/8.1.2 ; adapter `RAFALE_*` + police.
