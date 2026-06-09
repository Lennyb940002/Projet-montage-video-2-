# Musique de fond + Ducking (V1) — Design

**Date :** 2026-06-08
**Statut :** Design validé
**Contexte :** Sous-projet suivant le Pack Dynamisme. Objectif produit : faire ressentir « monté par un humain » dès le dépôt d'un audio, via une couche musicale qui respecte la voix.

## Décisions validées
- V1 = 5 fonctionnalités : fade in/out · sidechain ducking · pre-CTA gap · normalisation LUFS · sélection catégorie par règles.
- Reporter : BPM/beat sync · crossfade multi-tracks · analyse sémantique avancée.
- 2 catégories pour démarrer : **Luxury** et **Hype**.
- Réglages par défaut : `base_gain=-22 dB`, `duck_depth=-12 dB`, `fade_in=800 ms`, `fade_out=1200 ms`, `pre_cta_gap=1.2 s`, `target_lufs=-16`.

## Contraintes produit (intégrées)
1. **La voix prime toujours sur la musique** — garde-fou à 3 niveaux :
   - Plafond dur : `base_gain_dB ≤ -16 dB` (clamp avant rendu).
   - Plancher ducking : la musique reste ≥ 14 dB sous la voix pendant la parole.
   - **Test de discrimination automatique** post-rendu : RMS voix vs RMS musique sur fenêtres de parole → la voix doit dominer de ≥ 6 dB, sinon `RuntimeError` avec message clair (« voice dominance NN.N dB < 6.0 dB requis »).
2. **Mode debug musique** — `plan["music"]["debug"]` (toujours présent) + `music_debug.json` écrit à côté du rendu en mode démo. Contient : catégorie + raison(s) + score de confiance, track choisie, LUFS source / voix / cible / final, zones de ducking et de gap, paramètres effectifs après clamps.
3. **Schéma futur-compatible** : `plan["music"] = {"beds": [...], "accents": [...], "mix": ..., "debug": ...}` dès la V1. `accents` reste vide en V1 ; le `music_engine` itère déjà sur `beds` puis `accents` pour que demain (riser/impact/sweep/transition/accent) n'impose aucun refactor.

## Architecture (contrat strict — `docs/ARCHITECTURE.md`)
```
events (existants : keyword | nouveaux : voice_active, pre_cta_gap, intensity)
   ↓
Director._decide_music(events, ranges, duration, voice_audio_path)
   ↓
plan["music"]    (sérialisable JSON, voir §3)
   ↓
music_engine.build(plan["music"], voice_label="vmix")
   ↓
(extra_inputs, filter_fragment, out_label)
   ↓
montage.render (intègre dans son amix existant : voix + SFX + musique)
```

## Modules
| Fichier | Rôle |
|---|---|
| `backend/pipeline/music_bank.py` | Inventaire `MUSIC/<Category>/*.{mp3,wav,flac}` ; mesure LUFS + durée via ffmpeg `ebur128` ; cache JSON `.music_index.json` dans le dossier ; API `choose(category, target_dur, rng)` (déterministe via rng pour reproductibilité). |
| `backend/pipeline/music_engine.py` | **Purement exécutif** : transforme un `plan["music"]` en fragment ffmpeg (inputs + filter_complex + label de sortie). Itère sur `beds` puis `accents`. No-op si `music is None` ou `beds == []`. |
| `backend/pipeline/director.py` (+) | `_decide_music(events, ranges, duration, voice_audio_path)` ; helpers events `voice_active` (intervalles parlés à partir des tokens), `pre_cta_gap`, `intensity` (densité events). Implémente le **scoring catégorie** (voir §4) avec **fallback Luxury**. |
| `backend/pipeline/audio_meta.py` | Mesure LUFS d'un fichier audio via `ffmpeg ebur128` (réutilisable pour voix + musique). |
| `backend/config.py` (+) | `MUSIC_DIR`, `MUSIC = dict(base_gain_dB=-22, duck_depth_dB=-12, fade_in_ms=800, fade_out_ms=1200, pre_cta_gap_s=1.2, target_lufs=-16.0, voice_dominance_min_dB=6.0, category_default="luxury", confidence_threshold=0.60)`. |
| `montage.render` (+) | Ajoute la sortie de `music_engine.build()` dans son `amix` existant. Aucune logique métier ajoutée. |
| Frontend | Aucun changement V1 (la musique est automatique). |

## Structures de données

### Nouveaux Events (compatibles schéma existant)
```python
{"type": "voice_active", "start": float, "end": float}
{"type": "pre_cta_gap",  "start": float, "end": float, "importance": "high"}
{"type": "intensity",    "start": float, "end": float, "label": "calm"|"mid"|"peak", "importance": ...}
```

### Format `plan["music"]`
```python
plan["music"] = {
  "beds": [
    {
      "track": "<absolute path>",
      "category": "luxury" | "hype",
      "trim_start": 12.4,                 # offset dans la track source
      "start": 0.0,                       # quand ce bed commence dans la vidéo
      "duration": 13.57,                  # = duration vidéo (ou moins si plusieurs beds)
      "base_gain_dB": -22,                # après clamp <= -16
      "fade_in_ms": 800,
      "fade_out_ms": 1200,
      "duck": {
        "mode": "sidechain",              # "sidechain" V1 (zones reportées)
        "ratio": 6.0,
        "threshold_dB": -28,
        "attack_ms": 8,
        "release_ms": 280,
        "depth_dB": -12,                  # clamp pour respecter le plancher
        "side": "voice"                   # signal de référence
      },
      "gaps": [
        {"start": 11.4, "end": 12.6, "fade_out_ms": 250, "fade_in_ms": 200}
      ]
    }
  ],
  "accents": [],                          # V1 vide ; futur : riser/impact/sweep/transition
  "mix": {
    "target_lufs": -16.0,
    "voice_priority": True
  },
  "debug": {
    "category": "luxury",
    "confidence": 0.76,
    "reason": ["brand detected", "superlative detected"],
    "track": "MUSIC/Luxury/cinematic_calm_03.mp3",
    "lufs_voice": -16.4,
    "lufs_music_source": -10.2,
    "lufs_music_at_base": -22.4,
    "lufs_final_target": -16.0,
    "duck_depth_dB_effective": -12.0,
    "voice_dominance_dB": 7.8,            # mesuré post-rendu
    "gaps": [{"start": 11.4, "end": 12.6}],
    "fallback_used": False
  }
}
```

## Logique de sélection de catégorie (V1)

Heuristique simple basée **uniquement** sur les events existants (pas de RMS/courbe d'énergie en V1).

### Signaux extraits des events
- `n_cta` : nb d'events keyword dont `label` est un verbe CTA (réutilise `sfx_plan.is_cta`).
- `n_price` : nb d'events keyword dont `label` matche un prix.
- `n_number` : nb d'events keyword dont `label` matche un chiffre.
- `n_brand` : nb d'events keyword matchant `WATCH_BRANDS`.
- `n_superlative` : nb d'events keyword dont le `label` est dans la liste superlatifs.
- `n_high` : nb d'events keyword d'`importance: "high"`.
- `dur` : durée vidéo.

### Score « Hype »
Chaque condition vraie ajoute son poids ; score normalisé entre 0 et 1.

| Condition | Poids | Raison loggée si vraie |
|---|---:|---|
| `n_cta >= 2` | 0.30 | `"≥2 CTA"` |
| `n_price + n_number >= 2` | 0.25 | `"≥2 chiffres/prix"` |
| `dur < 20` | 0.15 | `"duration < 20s"` |
| `n_high / max(1, len(events)) >= 0.5` | 0.30 | `"densité events high"` |

### Score « Luxury »

| Condition | Poids | Raison |
|---|---:|---|
| `n_brand >= 1` | 0.35 | `"brand detected"` |
| `n_superlative >= 1` | 0.30 | `"superlative detected"` |
| `n_cta <= 1` | 0.15 | `"peu de CTA"` |
| `dur >= 20` | 0.20 | `"duration >= 20s"` |

### Décision
1. Calculer `hype_score`, `luxury_score`.
2. `winner = argmax(score)` ; `confidence = winner_score`.
3. **Si `confidence < MUSIC["confidence_threshold"]` (0.60)** → `category = MUSIC["category_default"]` (luxury), `reason = ["low confidence fallback"]`, `fallback_used = True`.
4. Sinon : `reason = liste des conditions vraies du gagnant`.

Cette logique est encapsulée dans `director._score_music_category(events, duration) -> dict` et **testée isolément** (déterministe, pas de hasard).

## Logique de ducking

V1 = **sidechaincompress** ffmpeg, signal de référence = piste voix (avant amix SFX).
- Réglages par défaut : `ratio=6, threshold=-28dB, attack=8ms, release=280ms`.
- **Clamp depth** : `depth_dB` calculé pour garantir que `lufs_voice - lufs_music_after_duck >= 14 dB`. Sinon réduit jusqu'à ce que le plancher soit respecté (et log « depth_dB clamped from X to Y »).
- Filtre ffmpeg : `[music][voice]sidechaincompress=threshold=…:ratio=…:attack=…:release=…[ducked]`. (La voix utilisée comme side n'est PAS modifiée.)

## Gap CTA (pre-CTA gap)

- Détection : Director cherche dans les events un `keyword` dont `is_cta(label) == True`. Premier trouvé → `cta_start`.
- Pose un `gap = {start: cta_start - MUSIC["pre_cta_gap_s"], end: cta_start, fade_out_ms: 250, fade_in_ms: 200}`.
- `music_engine` implémente le gap via une chaîne `volume='0:enable=between(t,s,e)'` + fades aux bords (préserve durée).

## Normalisation loudness

- **Source** : mesure LUFS de chaque track au scan banque (cache JSON).
- **Voix** : mesure LUFS de l'audio nettoyé une fois par rendu (~150 ms via ebur128).
- **Mix** : ne touche pas à la voix. Applique sur la musique un `volume` pour la placer à `base_gain_dB` sous la voix après normalisation, ce qui rend les tracks **interchangeables** sans surprise.
- Pas de limiter final V1 (mesure du clipping potentiel + log si dépassement).

## Test de discrimination voix/musique (garde-fou contrainte 1)

Post-rendu :
1. Extraire 5 fenêtres aléatoires de 200 ms **dans les zones `voice_active`** (mais en dehors des gaps).
2. Pour chaque fenêtre : mesurer RMS du mix final (voix+sfx+musique) et RMS de la voix seule (en route séparée).
3. Voice dominance moyenne = `RMS_voix - RMS_mix_diff_musique`. Si < 6 dB → `RuntimeError` avec contexte (« voice dominance NN dB, expected ≥ 6 dB »).
4. Valeur écrite dans `debug.voice_dominance_dB`.

Implémentation : `audio_meta.measure_dominance(mix_path, voice_path, voice_active_ranges)`.

## Protocole de démo finale (identique au Pack Dynamisme)

- Même audio, même texte, même seed clips, même plan vidéo Director.
- Seule différence : `plan["music"] = None` (BEFORE) vs `Director._decide_music(...)` (AFTER).
- Artefacts : `before.mp4`, `after.mp4`, `side_by_side.mp4` (vidéo identique gauche/droite, **audio différent**, sous-titres « MUSIC OFF / MUSIC ON » overlay).
- Rapport : temps rendu, taille, plan, events, **`music_debug.json`**.

## Erreurs & tests (hors-ligne)

- `music_bank.choose` : retourne déterministe pour `rng=Random(42)` ; gère dossier vide → `None`.
- `audio_meta.lufs_of` : valeur plausible (test sur sine 1 kHz à 0 dBFS → ~-3.0 LUFS attendu).
- `director._score_music_category` : tableaux d'events ciblés → vérifie catégorie + confiance + raisons + fallback.
- `director._decide_music` : produit un `plan["music"]` JSON-sérialisable avec `beds[0]`, `accents=[]`, `debug` complet.
- `music_engine.build` : `plan=None` ou `beds=[]` → no-op (`extra_inputs=[], filter=""`).
- `music_engine.build` avec bed mock : génère bien sidechain, fade in/out, gaps.
- `audio_meta.measure_dominance` : sur un mix où la voix est nettement plus forte que la musique → renvoie > 6 dB. Sur un mix inverse → < 6 dB.
- Tests d'intégration `montage.render` :
  - bed seul (pas de gap, pas de duck) → vidéo valide.
  - bed + duck + gap → vidéo valide, audio dominance OK.
  - test de **non-régression** : `plan["music"] = None` → bit-pour-bit identique au rendu sans musique (même seed).
- Test serveur `/preview` ne change pas (le câblage musique passe par le pipeline existant).

## Banque musique attendue

- `MUSIC/Luxury/*.mp3|wav|flac` (3-5 tracks recommandés au démarrage)
- `MUSIC/Hype/*.mp3|wav|flac` (3-5 tracks)
- Au premier scan, génération de `MUSIC/.music_index.json` (LUFS + durée de chaque track, ~30 ms par track).

## Hors périmètre (déjà acté)

BPM/beat sync · crossfade multi-tracks · analyse sémantique pour catégorie · accents (riser/impact/sweep…) — préparés par le schéma `accents=[]` mais pas implémentés.
