# AutoMontage — App desktop de montage vidéo automatisé

**Date :** 2026-06-07
**Statut :** Design validé (brainstorming)
**Auteur :** moilennybouche55@gmail.com + Claude

---

## 1. Objectif

Application **locale Windows**, à usage **personnel** (un seul utilisateur, ce PC), qui transforme un fichier audio (voix IA ElevenLabs) en vidéo verticale 9:16 prête à publier (TikTok/Reels/Shorts), en réutilisant le pipeline déjà développé dans `C:\Users\User\Downloads\Voix off` (`_montage2.py`).

Réduire le montage à **quelques clics**, tout en gardant une étape de **relecture/correction** manuelle (texte + audio) avant le rendu.

## 2. Contexte — l'existant réutilisé

Le pipeline actuel (scripts Python + ffmpeg) fait déjà :
- Nettoyage audio : suppression des silences (`SIL_KEEP = 0.10 s`, seuil `-35 dB`) + détection/coupe des reprises (phrases dupliquées exactes).
- Transcription : `faster-whisper`, modèle `small`, FR, `word_timestamps=True` (sans `initial_prompt` — sinon Whisper ne renvoie qu'un segment).
- Alignement texte exact ↔ audio via `difflib` (transfert des timings des mots Whisper sur le texte fourni).
- Sous-titres karaoké `.ass` : Arial Black, taille **84**, blanc → **jaune** mot à mot (`\k`), centré (Alignment 5), contour noir, en-tête ASS **avec champ `Name`** (bug virgule corrigé).
- Montage : clips muets choisis **aléatoirement** (un par phrase, sans répétition dans une vidéo), **zoom 30 %** (`ZOOM = 1.30`) pour masquer les watermarks de coin, concat + burn sous-titres.
- Rendu : 1080×1920, 30 fps, `libx264 -preset veryfast -crf 23`, `aac 192k`, `+faststart`.

Ce code sera **refactorisé en modules** dans le backend (voir §4).

## 3. Décisions de cadrage

| Sujet | Décision |
|---|---|
| Utilisateurs / cible | Moi seul, ce PC Windows. Pas d'installeur ni distribution. |
| Techno | **Electron** (UI) + **Python** (backend, sidecar) reliés par une **API HTTP locale** (127.0.0.1). Nécessite Node.js + Python. |
| Type d'audio | **Voix IA (ElevenLabs) uniquement.** Pas de détection de « euh »/bégaiements humains. |
| Sélection des clips | **Aléatoire** (comme l'existant). Pas de sélection sémantique, pas de « descriptions de scènes » (supprimées du périmètre — YAGNI). |
| Silences | **Supprimés automatiquement au dépôt** de l'audio (réversible via Annuler). |
| Reprises 🟡 | **Proposées, jamais coupées sans accord** de l'utilisateur. |
| Construction | **Par phases, MVP d'abord.** |
| Spec | Couvre **toute l'app** ; le plan d'implémentation commence par la **Phase 1**. |

## 4. Architecture

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│   FENÊTRE ELECTRON (UI)      │  HTTP  │   BACKEND PYTHON (sidecar)    │
│  - drag & drop audio         │ <────> │  1. transcription (whisper)  │
│  - éditeur transcription     │  local │  2. nettoyage audio          │
│  - surlignage 🟡 / 🔴        │  API   │  3. détection 🟡/🔴          │
│  - éditeur audio (waveform)  │        │  4. alignement texte↔audio   │
│  - aperçu vidéo + export     │        │  5. sous-titres .ass         │
└─────────────────────────────┘        │  6. sélection clips + rendu  │
                                        └──────────────────────────────┘
        │                                          │
   Banque de clips (dossier configurable)     Sortie vidéo 9:16
```

- Le backend Python démarre comme **processus sidecar** lancé par Electron, expose une petite API HTTP locale (FastAPI ou Flask), et reste sans état persistant entre projets (l'état du projet courant vit côté UI + fichiers de travail temporaires).
- Communication : requêtes JSON (lancer transcription, appliquer coupe, générer aperçu, exporter) ; les fichiers (audio, vidéo) sont échangés par chemins locaux.

### Modules backend (chacun isolé et testable seul)

1. **`transcribe`** — entrée : chemin audio ; sortie : segments + mots `(texte, start, end, prob)`.
2. **`audio_clean`** — entrée : audio + paramètres ; sortie : audio nettoyé + liste des plages coupées (silences). Réutilise la logique `silenceremove` + détection reprises.
3. **`detect`** — entrée : mots + segments ; sortie : zones 🟡 (reprises dupliquées exactes) et 🔴 (mots dont `prob` < seuil). Ne coupe rien automatiquement.
4. **`align`** — entrée : texte (corrigé) + mots Whisper ; sortie : tokens du texte avec timings (`difflib` + interpolation, monotonie).
5. **`subtitles`** — entrée : tokens timés ; sortie : fichier `.ass` karaoké (style validé).
6. **`montage`** — entrée : audio + `.ass` + banque de clips + réglages ; sortie : vidéo 9:16. Sélection aléatoire, zoom, concat, burn, encodage.

## 5. Interface (maquette validée)

Look sombre façon CapCut, **4 zones** :
- **Barre du haut** : logo, nom du fichier + réglages résumés, boutons **Générer l'aperçu** / **Exporter**.
- **Panneau gauche** : banque de clips (vignettes) + réglages (format 9:16, zoom, silences, style sous-titres).
- **Centre** : aperçu vidéo vertical 9:16 (sous-titre karaoké) + contrôles de lecture.
- **Panneau droit** : éditeur de transcription corrigeable, surlignage 🟡 (reprise → *Garder/Supprimer*) et 🔴 (à vérifier).
- **Panneau bas** : éditeur audio — forme d'onde (wavesurfer.js), sélection, **Lire / Pré-écoute / Couper / Supprimer**, zoom.

## 6. Comportement d'édition & flux de données

- **Édition du TEXTE** (orthographe, mot) : ne touche **pas** l'audio ni le timing ; sous-titres mis à jour **instantanément** (pas de re-transcription).
- **Coupe AUDIO** (outil « Supprimer sélection », ou *Supprimer* sur un 🟡/🔴) : retire réellement du son → **re-alignement automatique** → sous-titres recalés, mots supprimés retirés du texte.
- **Non destructif** : l'audio d'origine n'est jamais modifié ; l'app travaille sur une copie et garde la **liste des coupes**. **Annuler (Ctrl+Z)** disponible.
- **Ordre au dépôt** : transcription → silences auto → détection 🟡/🔴 affichée → relecture/correction → « Générer l'aperçu » → « Exporter ».

## 7. Règles de détection (voix IA)

- **Silences** : auto-supprimés (réglage `0,10 s`, `-35 dB`).
- **🟡 Jaune** : blocs de ≥ 4 mots répétés à l'identique (reprises), avec tolérance d'un petit bégaiement entre les deux occurrences (logique existante `find_retakes`).
- **🔴 Rouge** : mots dont la probabilité Whisper est sous un seuil (proxy fiable d'une prononciation douteuse / son bizarre). Jamais supprimés automatiquement.

## 8. Réglages par défaut

Format 9:16 (1080×1920, 30 fps) · modèle `small` · zoom clips `1.30` · silences `0,10 s` · sous-titres karaoké (Arial Black 84, jaune, ≤ 3 mots/bloc) · banque de clips = dossier configurable (défaut : clips muets actuels, versions muettes générées auto).

## 9. Phases d'implémentation

| Phase | Contenu |
|---|---|
| **1 — Cœur (MVP)** | Coquille Electron + backend Python + API · drag-drop audio · transcription · silences auto · éditeur de **texte** (correction + sous-titres live) · générer aperçu · exporter. |
| **2 — Détection** | 🟡 reprises + 🔴 mots peu sûrs · *Garder/Supprimer* · coupe audio + re-alignement. |
| **3 — Éditeur audio** | Forme d'onde · sélection · Couper/Supprimer · pré-écoute. |
| **4 — Finitions** | Gestion banque de clips (exclure des clips) · réglages · Annuler/Refaire. |

## 10. Erreurs & tests

- **Erreurs** : échecs ffmpeg/Whisper remontés à l'UI avec message clair (pas de plantage silencieux) ; audio illisible, banque de clips vide ou clips trop courts, espace disque → messages explicites.
- **Tests** : chaque module backend testé indépendamment sur un audio d'exemple (transcription, nettoyage, alignement, sous-titres, rendu) avant branchement UI.

## 11. Hors périmètre (YAGNI)

Sélection sémantique des clips · génération de descriptions de scènes · détection de « euh »/bégaiements de voix humaine · suppression auto des mauvaises prononciations · installeur/distribution/licences/mises à jour · montage multipiste manuel à la timeline.
