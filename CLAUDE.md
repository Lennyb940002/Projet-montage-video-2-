# CLAUDE.md — contexte de reprise (passerelle PC ↔ portable)

> Lu automatiquement par Claude Code. Ce fichier permet de **reprendre le projet
> sur un autre PC** (portable) sans tout réexpliquer. Dernière MAJ : 2026-07-06.

## C'est quoi ce projet

**AutoMontage** — moteur de génération + distribution de contenu Instagram/TikTok/
Facebook pour la marque de montres **Flowers Chrome**. Backend Python (FastAPI),
rendu vidéo **ffmpeg**, rendu images **Playwright/Chromium**, UI Electron.
Owner : Lenny (solo). Langue de travail : **français**.

## État actuel (IMPORTANT)

**Un système d'auto-post « vacances » tourne en autonomie via GitHub Actions.**
- Un **stock pré-généré** de 190 posts (14 j) est dans `stock/` + `stock/planning.json`.
- Le workflow `.github/workflows/post_stock.yml` (cron 30 min) exécute
  `deploy/post_from_planning.py`, qui poste les items **dus** via upload-post.com
  et coche `posted` dans le planning (re-commit auto).
- Contenu/jour : 5 reels + 2 carrousels (valeur/objection) + 3 stories promo +
  2 stories partage + 1 story question (≈13 posts). Reels → IG+TikTok+FB ;
  carrousels/stories → IG+FB.
- ⚠️ **Ne PAS regénérer / re-pousser le stock sans raison** pendant la période
  active (06→20 juillet) : ça écraserait l'avancement `posted`.

## Ce qui N'EST PAS dans le repo (à recopier / recréer sur le portable)

1. **Secrets** : `~/.automontage/settings.json` (clés Gemini, token+user upload-post,
   bot Telegram) et `~/.oci/`. À recréer à la main. **Jamais committer.**
2. **Assets lourds** (gitignorés) : banque de clips vidéo, musique, tuiles catalogue,
   photos produit, SFX, fond vidéo. Chemins dans `backend/config.py`.
   → Sur le portable : recopier ces dossiers, ou **adapter les chemins Windows**
   de `config.py` (`SILENT["clips_dir"]`, `music_dir`, `PHOTOS["dir"]`, etc. —
   ils pointent vers `C:\Users\User\...` du PC de bureau).
3. Sans ces assets, la **génération** ne tourne pas, mais le **code** et le stock
   déjà généré sont là.

## Setup portable

```bash
pip install -r backend/requirements.txt      # Python 3.13
python -m playwright install chromium         # pour les carrousels/stories
# ffmpeg dans le PATH (voir FFMPEG_BIN dans backend/config.py)
```

## Commandes clés

```bash
python -m pytest backend/tests -q -k "not e2e"      # tests (doivent être verts)
python deploy/generate_batch_1a.py                  # lot 30 reels (formats 1A)
python deploy/generate_special_formats.py           # choix 4 montres + devine le prix
python deploy/generate_stock_full.py                # stock complet vacances (LOURD)
python deploy/shift_planning.py YYYY-MM-DD          # décaler la date de début du planning
```

## Architecture

- `backend/silent/` — **moteur reels** : ContentStrategy → `policy.py` (SEUL décideur)
  → `VideoRecipe` → `render.py` → store. 5 formats « guide 2026-07-05 » :
  `test, revelation_psy, trahison, perception, test_perso` (split_3, 3 montres).
  Contenu dans `backend/silent/banks/` (hooks + `familles.json`).
- `backend/silent/special_render.py` — formats spéciaux : **choix 4 montres** (grille
  2×2 sur fond vidéo) + **devine le prix** (séquence reveal).
- `backend/posts/` — carrousels (`carousel.py`, Playwright), stories (`story.py`,
  `promo.py`, `story_question.py`), tuiles catalogue.
- `backend/distribution/` — scheduler local (Telegram) + `uploadpost.py`.
- `deploy/` — générateurs de lots, posteur GitHub Actions, guides.
- `docs/superpowers/` — **specs & plans** (lis-les avant de reprendre une feature).

## Conventions / décisions prises

- **Rollback V1 (2026-07-03)** : la refonte « V2 » (rebrand Ascendant Magnétique,
  noms FC Aurora…, Canon, captions/stories V2) a été **rejetée**. Le code V2 est
  gardé **inerte** sur disque (`canon.py`, `captions_v2.py`, `stories_v2.py`, tests
  V2 `pytest.mark.skip`). Ne pas le réactiver sans demande explicite.
- **Formats génériques bannis** (guide 2026-07-05) : comparison, vote, elimination,
  reveal-suspense « regarde jusqu'au bout » → `mechanic_bias=0`. Ne pas les relancer.
- **Labels décidés par la policy** (`recipe.labels`), jamais hardcodés dans le
  renderer (fail dur si un format 1A arrive sans labels).
- Prix affiché : **194,90 €** (tuiles) ; promo : 194,50 barré → 179.
- Travailler avec jugement : contredire si nécessaire, valider sur du réel avant
  d'élargir, garde-fous avant actions coûteuses/irréversibles.

## Points d'attention (état au 2026-07-06)

- **upload-post** : compte identifiant `Flowers` ; login web récupéré via « mot de
  passe oublié » sur l'email de création (voir `settings.json` local, pas ici).
  TikTok + Facebook reconnectés. Token API sans expiration.
- **Sécurité** : plusieurs secrets ont transité en clair par le chat →
  **à régénérer** (token upload-post, clés Gemini, bot Telegram, PAT GitHub).
- **Repo** : `github.com/Lennyb940002/Projet-montage-video-2-` (privé), branche `main`.
  Secrets GitHub Actions : `UPLOADPOST_TOKEN`, `UPLOADPOST_USER` (le workflow
  accepte aussi `UPLOAD_POST_*`).
- **Limite connue** : banque carrousel valeur = 5 scripts → répétitif sur 14 j.
  Banque clips vidéo = 26 → montres qui se répètent.

## Prochaines phases (non faites)

Reels : 1B (projection, vibe, mood, red/green flag, quel-homme…), Fiche d'identité
(carte texte), Budget flash + SFX, **montage rythmé multi-écrans** (le gros morceau
qui donnera un vrai « look »). Cf `docs/superpowers/` pour les specs/plans.
