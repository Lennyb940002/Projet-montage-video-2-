# Architecture — Moteur de réalisation auto

Ce document fixe le contrat d'architecture du projet. Toute nouvelle fonctionnalité doit le respecter.

## Principe : pipeline d'événements normalisés + Director unique

```
                detect_events                build_plan
   tokens  ──────────────────►  events  ───────────────►  plan
   ranges                                   (Director)     │
   audio                                                   ▼
                                              ┌────────────┴────────────┐
                                              ▼            ▼            ▼
                                          subtitles      motion      transitions
                                              │            │            │
                                              ▼            ▼            ▼
                                         renderers (exécutent, ne décident pas)
```

### 1. Détection (`backend/pipeline/keywords.py`, plus tard `analysis.py`, `broll.py`...)
**Rôle** : détecter et classer des évènements. **Aucune décision de montage.**

Schéma d'un évènement (source unique de vérité) :
```python
Event = {
    "type": "keyword" | "cut" | "sentence_start" | "emotion" | "topic" | "broll_match" | ...,
    "label": str,
    "start": float,
    "end": float,
    "importance": "high" | "normal" | "low",
}
```
Exemple :
```python
{"type": "keyword", "label": "Rolex", "start": 4.2, "end": 4.8, "importance": "high"}
```

### 2. Décision (`backend/pipeline/director.py`)
**Seule** source de décisions de montage. `build_plan(events, ranges, duration)` consomme la liste d'`events` et produit un **plan** typé :

```python
plan = {
    "subtitles":   [SubLine, ...],      # lignes prêtes à dessiner
    "motion":      [MotionOp, ...],     # opérations de motion par clip
    "transitions": [Transition, ...],   # transitions aux cuts
    # futurs : "music", "overlays", "broll"
}
```
Le Director peut ENRICHIR son cerveau (sémantique, B-roll, règles complexes) **sans aucun changement aux renderers**.

### 3. Exécution (`subtitles.py`, `montage.py`)
Les renderers sont **purement exécutifs**. Ils prennent les structures du plan et les rendent. **Zéro logique métier** ne doit être ajoutée dans ces modules.
- `subtitles.build_ass(plan["subtitles"], path, style_preset)` — dessine ce qu'on lui donne.
- `montage.render(audio, ass, ranges, out, plan=plan)` — applique motion + transitions tels que décrits.

## Règles de discipline
1. **Aucune règle métier dans un renderer.** Si tu te dis "si keyword → pop", c'est dans le Director.
2. **Aucune liste de mots/règles dispersée.** Toute liste de mots-clés vit dans `keywords.py`.
3. **Tout nouveau signal = nouveau type d'`Event`**, pas un argument ad hoc.
4. **Tout nouveau rendu = nouvelle clé dans `plan`** (`plan["music"]`, `plan["overlays"]`...), un moteur d'exécution dédié, et le Director qui décide.
5. **Le plan est versionnable et inspectable** (sérialisable JSON) → tests, debug, futur "Director-UI".

## Motion V1 — robustesse > complexité (validé)
- **Zoom de base par clip** : zoom **constant varié par clip** (rotation 1.05 / 1.10 / 1.15 / 1.20) avec centre / léger décalage → impression de vie sans aucun risque.
- **Punch zoom** sur mots-clés : courte fenêtre de zoom plus serré.
- **Shake léger** sur événements importants (`crop x/y` oscillants).
- **Pas de `zoompan`** en V1 (même s'il marche) : priorité fluidité et fiabilité. Ken Burns animé pourra être un nouveau type de `motion` plus tard sans toucher au renderer.

## Roadmap après Pack Dynamisme (gravée)
1. **Pack Dynamisme** (en cours) : emphase sous-titres + motion V1 robuste + transitions length-preserving.
2. **Musique de fond + ducking** : `plan["music"]`, module `music_engine.py` exécutif.
3. **B-roll sémantique** : `analysis.py` produit des events, `broll.py` propose des matches, Director arbitre, `montage.render` applique.
4. **Director enrichi** (règles « jamais > 3 s sans changement », « overlay sur chiffre »...).
