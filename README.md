# AutoMontage — Flowers Chrome content engine

Moteur de génération et de distribution de contenu Instagram/TikTok pour la marque
**Flowers Chrome** (montres). Projet privé. Application Electron + backend Python (FastAPI),
rendu vidéo via **ffmpeg**, images via **Playwright/Chromium**.

> ⚠️ **Repo de CODE uniquement.** Les assets lourds et les secrets ne sont PAS versionnés
> (voir §« Ce qui n'est PAS dans le repo »). Cloner ne suffit pas à faire tourner la prod :
> il faut aussi copier les banques d'assets et recréer les réglages.

## Ce qui est dans le repo

- `backend/silent/` — **Silent Content Engine** : reels sans voix-off. ContentStrategy →
  Policy (seul décideur) → VideoRecipe → Renderer → Store. 5 formats « guide 2026-07-05 »
  (`test`, `revelation_psy`, `trahison`, `perception`, `test_perso`), banques de contenu
  dans `backend/silent/banks/` (hooks, `familles.json`).
- `backend/silent/special_render.py` — formats spéciaux : **choix 4 montres** (grille 2×2 sur
  fond vidéo) + **devine le prix** (séquence reveal).
- `backend/posts/` — carrousels valeur/objection (Playwright), stories promo, tuiles catalogue.
- `backend/distribution/` — scheduler (Telegram bot) + upload-post.com (IG/TikTok) + caption SEO.
- `backend/pipeline/` — ancien pipeline montage voix-off (SFX, sous-titres).
- `deploy/` — générateurs de lots (`generate_batch_1a.py`, `generate_special_formats.py`,
  `prototypes_new_formats.py`), déploiement Oracle (`setup.sh`, `oracle_autolaunch.py`).
- `frontend/` — UI Electron.
- `docs/superpowers/` — specs et plans d'implémentation.

## Ce qui n'est PAS dans le repo (à copier / recréer sur un autre PC)

1. **Banque de clips vidéo** (montres au poignet, générés Gemini→Kling) :
   `…\Downloads\Montage video\Banque video\<modèle>\` — plusieurs Go.
2. **Musique** : `…\Downloads\Montage video\Musique\`.
3. **Tuiles catalogue** : `…\Desktop\Catalogue montre\_flowers_tiles\`.
4. **Fond(s) vidéo** : `…\Vidéo montage fond\`.
5. **Secrets** — `~/.automontage/settings.json` (clés Gemini, token upload-post, bot Telegram)
   + `~/.oci/` (accès Oracle). **À recréer à la main.** Ne jamais committer.

> Les chemins sont dans `backend/config.py` (`SILENT["clips_dir"]`, `music_dir`, etc.).
> Sur un autre PC (ex. portable), adapter ces chemins ou reproduire l'arborescence.

## Setup rapide

```bash
pip install -r backend/requirements.txt   # backend Python (Python 3.13)
# ffmpeg requis dans le PATH (voir FFMPEG_BIN dans backend/config.py)
cd frontend && npm install                # frontend Electron (optionnel)
```

## Commandes clés

```bash
# Lot de test 30 reels (5 formats 1A) -> output/batch_1a/ + manifest.json
python deploy/generate_batch_1a.py

# Lot formats spéciaux (choix 4 montres + devine le prix) -> output/special_formats/
python deploy/generate_special_formats.py

# Tests
python -m pytest backend/tests -q -k "not e2e"

# Scheduler (prod auto : vidéos + carrousels + stories, bot Telegram)
python -m backend.distribution.scheduler
```

## État actuel (2026-07-05)

- Branche principale : `main`.
- 5 formats reels 1A opérationnels ; anciens formats génériques désactivés (biais 0).
- 2 formats spéciaux industrialisés (choix 4 montres, devine le prix).
- ⚠️ **TikTok** : accès à reconnecter sur upload-post.com.
- ⚠️ **Scheduler** : redémarrer pour charger le nouveau code.
- Suite : Phases 1B / Fiche d'identité / Budget flash+SFX / montage rythmé (voir `docs/`).
