# ✨ Boost Hook — Design

**Date :** 2026-06-07
**Statut :** Design validé
**Contexte :** Fonctionnalité ajoutée à l'app AutoMontage (Electron + Python). Objectif utilisateur : **accrocher plus de spectateurs sur le hook** (rétention des premières secondes).

## Objectif

Un bouton/interrupteur **✨ Boost Hook** qui, à la génération de l'aperçu et à l'export, applique automatiquement un montage plus dynamique (visuel + effets sonores), avec un focus particulier sur les 3,5 premières secondes.

## Décisions validées

- **SFX** : fournis par l'utilisateur dans un dossier `SFX/` (configurable). Rangés par mot-clé dans le nom de fichier : `impact*`, `whoosh*`, `riser*`. L'app pioche aléatoirement dans la bonne catégorie. **Dossier vide → boost visuel seul, sans erreur.**
- **Portée** : hook (0-3,5 s) ET toute la vidéo.
- **Effets** (combo éprouvé, validé) :
  - **Hook 0-3,5 s** : cuts plus rapides (~0,8 s/clip), **zoom punch** sur la 1ʳᵉ image, **impact + flash blanc bref** sur la première frame.
  - **Toute la vidéo** : **zoom progressif léger** (Ken Burns) sur chaque clip, **whoosh** sur les changements de clip (dosé).
- Le boost est **optionnel** (interrupteur off par défaut).

## Architecture

Réutilise le pipeline existant. Le boost est un **mode du moteur de montage** :

- **`backend/pipeline/sfx.py`** (nouveau) : `pick(category, sfx_dir)` → chemin d'un SFX aléatoire de la catégorie, ou `None` si absent. `list_sfx(sfx_dir)`.
- **`backend/pipeline/montage.py`** (modifié) : `render(..., boost=False, sfx_dir=...)`.
  - Calcul des plages de clips : si `boost`, le hook (0-3,5 s) est redécoupé en sous-segments ~0,8 s (plus de clips) ; le reste inchangé (1 clip/phrase).
  - Filtre vidéo par clip : si `boost`, ajout d'un `zoompan` (Ken Burns léger ; zoom punch plus marqué sur le 1ᵉʳ clip) + un **flash** (overlay blanc ~0,12 s) au tout début.
  - Audio : piste voix + SFX mixés. Pour chaque évènement (impact à t=0, whoosh à chaque changement de clip), un input SFX décalé (`adelay`) puis `amix` avec la voix. Volume SFX modéré.
- **`backend/service.py`** : `make_video(..., boost=False)` transmet à `render`.
- **`backend/server.py`** : `VideoReq` gagne `boost: bool = False` ; `/preview` et `/export` le passent.
- **Frontend** : interrupteur **✨ Boost Hook** près de « Générer/Exporter », transmis aux appels.

## Réglages (config.py)

`SFX_DIR` (défaut : `<projet>/SFX`), `HOOK_DUR = 3.5`, `HOOK_CUT = 0.8`, volumes SFX, intensités de zoom.

## Erreurs & tests

- **Erreurs** : SFX manquants → ignorés (visuel seul) ; échec ffmpeg → message clair (déjà en place).
- **Tests** :
  - `sfx.pick` : retourne un fichier de la bonne catégorie / `None` si vide.
  - `montage.render(boost=True)` produit une vidéo 1080×1920 valide **avec** et **sans** dossier SFX (mix audio présent quand SFX dispo).
  - Hook redécoupé : plus de segments en mode boost qu'en mode normal pour un audio donné.

## Hors périmètre (évolution future)

Génération automatique de **2-3 variantes de hook** pour A/B tester en conditions réelles (répond à « plus de gens qui accrochent »). Musique de fond. Beat-sync.
