# Audio « machine de guerre » — nettoyage adaptatif + détection fine

**Date :** 2026-06-08
**Statut :** Design validé
**Contexte :** Renforcer le nettoyage et la détection audio de AutoMontage, **sans jamais dégrader** le rendu. La détection ne coupe rien (signalé 🟡/🔴, validé par l'utilisateur) ; le nettoyage reste conservateur, adaptatif et réversible.

## Décisions validées
- Nouveau nettoyage **adaptatif par défaut** (pas de toggle), avec **non-régression** vérifiée.
- Détection plus fine = **plus de zones à valider**, jamais de coupe auto.

## Axe 1 — Nettoyage (`backend/pipeline/audio_clean.py`)
- **`noise_floor(path)`** : mesure le plancher de bruit via `ffmpeg astats` ("Noise floor dB"). Fallback à une valeur fixe si indisponible.
- **`remove_silences`** : seuil de silence **adaptatif** = `noise_floor + marge` (config), borné dans une plage sûre (ex. entre -55 et -28 dB) ; conserve un **souffle** (`keep`, défaut 0,12 s). Par construction on ne retire que ce qui est sous le seuil → **jamais de parole**.
- Réglages dans `config.py` : `SILENCE = dict(keep, margin_db, floor_min, floor_max)`.

## Axe 2 — Détection (`backend/pipeline/detect.py`) — signalé, jamais coupé
- **Quasi-doublons** : `find_retakes` accepte une similarité ≥ `FUZZY_RATIO` (défaut 0,85, `difflib`) en plus de l'égalité exacte → reprises avec légères variations.
- **Mots peu sûrs (relatif)** : seuil = `clamp(moyenne_prob - delta, lo, hi)` au lieu d'un 0,5 fixe ; inclut les **mots tronqués** (prob très basse ET durée anormalement courte).
- **Longues pauses** : `long_pauses(words, min_gap)` → plages des silences résiduels anormalement longs (🟡).
- `detect(words)` renvoie `{retakes, lowconf, pauses}`.

## UI (`frontend/renderer.js`) — minimal
- `setState` lit `res.detect.pauses` ; `buildRegions` ajoute les **pauses** comme zones 🟡 (mêmes interactions Garder/Supprimer). `keepRegion` gère le retrait local d'une pause. Aucune autre logique touchée. (Reprises floues et lowconf relatif passent par les listes existantes → zéro changement UI pour eux.)

## Sécurité & non-régression
- Détection = additive (zones à valider) → ne peut pas dégrader.
- Nettoyage : seuil borné + souffle conservé ; **test de non-régression** : sur l'échantillon, durée nettoyée ≤ durée d'origine et > 40 %, et aucune coupe sous le plancher de parole.
- Tout réglable dans `config.py` ; coupes réversibles (Annuler existant).

## Tests (hors-ligne)
- `noise_floor(sample)` → flottant dB plausible (< -20).
- `remove_silences` adaptatif → fichier valide, plus court mais pas vidé.
- `find_retakes` floue → détecte une reprise quasi-identique (variation légère).
- `low_confidence` relatif → flagge un mot nettement sous la moyenne, pas tout.
- `long_pauses` → détecte un gap > seuil ; vide si pas de gap.
- `detect` → renvoie les 3 clés.

## Hors périmètre
Mastering (normalisation LUFS, débruitage, de-ess, EQ) — non retenu cette fois.
