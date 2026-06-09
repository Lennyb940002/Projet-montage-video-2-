# Asset Audit (Ticket A) — Design

**Date :** 2026-06-09
**Statut :** Design en cours
**Contexte :** Le rendu vidéo est saboté par la qualité des assets sources (watermarks, sous-titres incrustés, clips hors-sujet). Avant d'ouvrir le chantier B-roll sémantique (Ticket C — Pexels), on doit savoir quel % de la banque actuelle est utilisable. Pour ça : audit OCR + heuristique watermark sur chaque clip, rapport JSON, rejet automatique.

## Décisions validées
- Approche hybride **OCR + heuristique watermark** (pas de LLM, pas d'API payante).
- Sortie : un JSON par clip avec status `accept`/`reject` + raisons + métadonnées bonus.
- Rejet ENSUITE branché dans `_pick_clips` (Ticket B).

## Modules

| Fichier | Rôle | Lignes estimées |
|---|---|---|
| `backend/pipeline/asset_audit.py` | OCR + watermark scan d'un clip | ~150 |
| `backend/pipeline/asset_index.py` | Indexer / scanner / cache JSON | ~80 |
| `tools/audit_clips.py` (script) | CLI pour scanner une banque entière | ~50 |
| `backend/tests/test_asset_audit.py` | Tests unitaires | TDD |

## Schéma JSON par clip
```python
{
  "path": "C:/.../Clips/Muet/clip01.mp4",
  "duration": 17.2,
  "scanned_at": "2026-06-09T...",
  # OCR
  "text_detected": true,
  "ocr_density": 0.27,         # nb tokens texte / 5 frames
  "text_regions": 4,           # nb max de zones texte sur une frame
  "ocr_samples": [             # ce qui a été lu (pour debug)
    {"t": 1.7, "texts": ["@cebutimepieces", "POV"]},
    ...
  ],
  # Watermark
  "watermark_suspected": true,
  "watermark_confidence": 0.91,
  "watermark_zones": ["bottom_left"],
  # Bonus (Ticket A) — utiles pour Ticket B-roll sémantique
  "avg_brightness": 0.61,
  "blur_score": 0.83,
  # Décision finale
  "status": "rejected",        # "accepted" | "rejected"
  "reasons": ["watermark", "embedded_text"]
}
```

## Algo OCR (étage 1)
1. Extraire 5 frames à 10/30/50/70/90% de la durée du clip.
2. Pour chaque frame : EasyOCR FR+EN → liste de tokens avec position (bbox).
3. Agréger :
   - `text_detected` = vrai si ≥1 token textuel sur ≥2 frames.
   - `ocr_density` = total tokens / 5 frames.
   - `text_regions` = max nb de bboxes distinctes sur une frame.
   - `ocr_samples` = top tokens par frame (pour debug humain).

## Heuristique watermark (étage 1, parallèle à OCR)
Pour chaque texte détecté, calculer son **niveau de suspicion watermark** :
- **Zone** : bbox dans une des 4 zones de coin (≤15% du bord) → +0.30
- **Persistence** : même texte sur ≥3 frames → +0.30
- **Marqueur `@`** : token commence par `@` → +0.30
- **Opacité partielle** : texte semi-transparent (gris/blanc translucide) → +0.10

`watermark_confidence` = somme clampée [0, 1]. Si ≥0.6 sur au moins une zone → `watermark_suspected = true`.

## Règles de rejet (étage 2)
```python
if watermark_confidence > 0.8:    reject("watermark")
if ocr_density > 0.15:            reject("embedded_text")
if text_regions >= 3:             reject("embedded_text")
```

## Cache
Comme `music_bank`, JSON dans `<clips_dir>/.asset_audit.json`, invalidé par `mtime` du fichier. Re-scan seulement les fichiers nouveaux/modifiés.

## Performance attendue
- OCR EasyOCR : ~0.5-1.5 s par frame sur CPU → ~3-8 s par clip
- 40 clips actuels → ~2-5 minutes de scan unique (puis cache)

## Tests
- Clip synthétique sans texte → `text_detected=False`, `accept`
- Clip avec watermark `@nom` en coin → `watermark_suspected=True`, `reject`
- Clip avec sous-titres TikTok plein écran → `text_regions >= 3`, `reject`
- Cache invalidé sur `mtime` modifié

## Hors périmètre Ticket A
- Détection de visages (mentionnée comme bonus mais reportée — pas critique V1)
- Détection « watch » (B-roll sémantique = Ticket C)
- Tags catégorie/style (Ticket C)

## Suite (Tickets B/C)
- **B** : brancher `asset_audit.is_accepted(path)` dans `montage._pick_clips`
- **C** : Pexels ingestion remplit la banque avec des clips déjà filtrés
