# Notes de design — Musique de fond + Ducking (prochain sous-projet)

À respecter STRICTEMENT le contrat d'architecture (`docs/ARCHITECTURE.md`).

## Pipeline
```
                                       Director
                                          │
  events (existants + nouveaux)  ────────►│────────► plan["music"]   ◄── consommé par music_engine
                                          │                              (exécutif uniquement)
                                          ▼
                                    plan complet
                                  {subtitles, motion,
                                   transitions, music, ...}
```

## Nouveaux types d'`Event` (ajoutés par un module `analysis.py` léger)
- `energy_low` / `energy_mid` / `energy_high` : courbe d'énergie sur la voix → choisir la **catégorie** musicale.
- `voice_active` : intervalles parlés (utiles au ducking).
Réutilise `keyword` existant pour intensifier la dynamique musicale aux moments forts.

## `plan["music"]`
Structure JSON typée (un seul track pour V1) :
```python
{
  "track": "<chemin/MP3>",          # choisi par le Director dans la banque
  "start": 0.0,                     # offset de lecture dans la piste source
  "end": <duration_video>,          # se coupe net en fin de vidéo
  "base_gain_dB": -22,              # niveau "lit musical" sous la voix
  "fade_in_ms": 600,
  "fade_out_ms": 800,
  "duck_zones": [                   # ducking dynamique sous voix
    {"start": 0.0, "end": 12.3, "gain_dB": -12, "attack_ms": 80, "release_ms": 260}
  ]
}
```
- Le Director **décide** : quelle catégorie (motivation / luxe / business / storytelling / éducatif) selon les events, quels intervalles ducker, à quel volume.
- Les `duck_zones` viennent des events `voice_active`.

## Banque de musiques (utilisateur)
- Dossier `MUSIC/` rangé par catégorie : `MUSIC/Motivation/`, `MUSIC/Luxe/`, etc.
- Module `backend/pipeline/music_bank.py` (analogue à `sfx.py`) :
  - `list_music(dir)`, `pick(category, target_dur, energy)` → chemin déterministe (cohérence intra-vidéo).
  - Mesure du **loudness intégré** (LUFS) via ffmpeg `ebur128` pour égaliser entre pistes.

## Renderer `music_engine.py` (purement exécutif)
- Reçoit `plan["music"]`. Ajoute un `-i <track>` côté ffmpeg.
- Filtres : `atrim → volume(base_gain_dB) → afade → sidechaincompress` (ducking sous la voix) → `amix` avec la voix + SFX existants.
- Réutilise le `amix` actuel du `montage.render`. Aucune logique métier ici (juste l'exécution).

## Décisions à prendre quand on attaquera
1. Algo de choix de catégorie (règles simples vs énergie moyenne).
2. Faut-il un fade out **avant** le CTA pour le faire ressortir ? (probablement oui, +1 type d'event `pre_cta_gap`).
3. Volume base : -22 dB (sous voix typique -16 LUFS) → loudness final ≈ -16 LUFS.
4. Faut-il proposer plusieurs candidats au Director et choisir par énergie ?

## Garde-fous
- Pas de musique = vidéo identique à aujourd'hui (`plan["music"]` absent → music_engine no-op).
- Tests : ducking actif réduit bien la musique pendant la voix (mesure RMS sur fenêtre).
- Coût rendu : musique = 1 input + 1 filtre amix → quasi gratuit (mesuré).
