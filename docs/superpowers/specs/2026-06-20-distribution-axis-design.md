# Axe Distribution — Design

**Date :** 2026-06-20
**Statut :** Design validé (en attente revue du spec avant plan d'implémentation)
**Contexte :** L'axe production (Silent Content Engine) génère des vidéos. L'axe distribution
les fait **valider sur Telegram puis publier automatiquement** sur Instagram + TikTok, à
4 créneaux/jour, sans intervention manuelle (sauf le veto Telegram).

## Objectif
À 9h / 12h / 18h / 22h (Europe/Paris) : générer une vidéo, l'envoyer sur Telegram pour
validation, et la publier (ou non) selon la réponse de l'utilisateur. Tourne en continu,
host-agnostic (PC en test → VM Oracle Cloud Free en prod).

## Décisions validées
- **Posting** : `upload-post.com` (API dev-first, l'intermédiaire est l'app auditée → zéro
  paperasse Meta/TikTok, post public, ~gratuit au volume). Intégration **directe** (pas de
  couche d'abstraction lourde — "le plus rapide à l'emploi").
- **Validation** : bot Telegram (**Bot API**), vidéo + boutons inline ✅/❌/🔄, timeout 30 min.
- **Caption** : description SEO via **Gemini** (clé fournie) à partir des montres + concept ;
  fallback sur le générateur template existant si clé absente.
- **Runtime** : programme Python always-on, déployé sur **Oracle Cloud Always Free** (gratuit
  24/7). Host-agnostic : tourne pareil sur PC (test) et VM.
- **Secrets** : `~/.automontage/settings.json` (hors git). Champs : `gemini_key`,
  `uploadpost_token`, `telegram_bot_token`, `telegram_chat_id`.

## Flow (machine à états)
```
Scheduler (APScheduler, cron 9/12/18/22h Europe/Paris)
  └─ generate() : Policy.decide → render_recipe → MP4
       └─ caption() : Gemini SEO (sinon template)
       └─ Telegram.send : vidéo + caption + boutons [✅ Publier][❌ Skip][🔄 Refaire]
            ├─ ✅  → post() upload-post (IG+TikTok) → statut=posted
            ├─ ❌  → statut=skipped (rien posté)
            ├─ 🔄  → regenerate (nouvelle Policy.decide, nouveau seed) → renvoie
            └─ ⏱  30 min sans réponse → post() (auto) → statut=auto_posted
```
État persisté en SQLite (réutilise `silent.db`). Table `distribution_posts` :
`id, created_at, video_path, mechanic, content_angle, layout, asset_ids, caption,
status (pending|posted|auto_posted|skipped|failed), tg_message_id, decided_at`.

## Architecture — 3 couches + secrets
```
backend/distribution/
├── uploadpost.py    post(video_path, caption, platforms) -> {ok, ids|error}  (exécutif)
├── caption_seo.py   build_caption(recipe, model_names) -> (caption, hashtags)
│                       Gemini si clé, sinon template ; 1-2 hashtags max
├── telegram_bot.py  send_for_approval(video, caption) + boutons + callbacks + timeout
├── store.py         table distribution_posts (insert/update/query par statut)
└── orchestrator.py  run_slot() : generate -> caption -> approval -> post ; colle tout
backend/distribution/scheduler.py   APScheduler : 4 créneaux -> orchestrator.run_slot()
```
- **uploadpost.py** : POST multipart (vidéo + caption + plateformes) avec `uploadpost_token`.
  Pas de tunnel public nécessaire (≠ IG Graph). Non-bloquant : renvoie {ok:false, error} au
  lieu de crash.
- **caption_seo.py** : prompt construit depuis les noms de montres (via `SILENT['models']`) +
  mécanique + concept → Gemini `gemini-2.x` REST → description SEO + 1-2 hashtags. Fallback
  template (`backend.pipeline.caption`) si pas de clé ou erreur.
- **telegram_bot.py** : `python-telegram-bot` (long-polling, OK sur VM always-on). Envoie la
  vidéo, gère les callbacks des boutons, applique le timeout 30 min (job différé APScheduler).
- **orchestrator.run_slot()** : orchestration pure, non-bloquante (toute erreur → alerte
  Telegram + statut=failed, le scheduler continue).

## Caption SEO (Gemini)
Entrée : `{mechanic, concept, montres:[noms], goal}`. Sortie : description FR optimisée SEO
(mots-clés horlogers, marques, occasion) + **1-2 hashtags max**. Prompt système : ton premium,
pas de spam de hashtags, intégrer les noms exacts des montres. Clé lue dans settings.

## Gestion d'erreurs (non-bloquant absolu)
- Render échoue → alerte Telegram "génération KO créneau Xh", statut=failed, scheduler continue.
- upload-post échoue → alerte Telegram avec l'erreur, statut=failed, pas de retry auto V1.
- Gemini échoue/clé absente → fallback caption template (jamais bloquant).
- Telegram down → log + statut reste pending (on ne poste pas sans validation/timeout fiable).

## Déploiement — Oracle Cloud Always Free (guide J-jour)
1. **(Utilisateur)** Créer compte Oracle Cloud → Compute → Instance → image **Ubuntu 22.04**,
   shape **Always Free** (VM.Standard.A1.Flex ARM ou E2.1.Micro) → télécharger la clé SSH.
2. **(Utilisateur)** Donne l'IP publique + la clé SSH.
3. **(Script fourni)** `deploy/setup.sh` : `apt install ffmpeg python3-venv git`, clone repo,
   `pip install -r requirements.txt`, crée `~/.automontage/settings.json` (secrets), installe
   un service **systemd** `automontage-dist` qui lance `python -m backend.distribution.scheduler`.
4. Le service tourne 24/7, redémarre au boot. Logs via `journalctl -u automontage-dist`.
- Fallback si Oracle pénible (signup/capacité ARM) : Railway/Render (~5€/mo, deploy via Git).
- **Host-agnostic** : le même `python -m backend.distribution.scheduler` tourne sur PC (test).

## Tests (TDD, mocks — rien posté en vrai)
- **uploadpost** : mock HTTP → post() renvoie {ok} ; erreur HTTP → {ok:false, error} (non-bloquant).
- **caption_seo** : mock Gemini → caption + ≤2 hashtags ; pas de clé → fallback template.
- **store** : insert/update statut, query pending.
- **orchestrator (machine à états)** : ✅→posted, ❌→skipped, 🔄→regenerate (2e recipe ≠), timeout→auto_posted, erreur render→failed (scheduler survit).
- **scheduler** : 4 jobs aux bons créneaux (Europe/Paris), déclenche run_slot (mock).
- **telegram_bot** : mock Bot API → send + parsing callbacks.

## Découpage en sous-projets (ordre de build)
1. **uploadpost.py** + champ Réglages token + **test post réel** (1 vidéo validée par l'utilisateur)
2. **caption_seo.py** (Gemini + fallback) + test
3. **telegram_bot.py** : envoi + boutons + machine à états (timeout)
4. **scheduler.py** + orchestrator : les 4 créneaux qui orchestrent tout
5. **Déploiement Oracle Free** (setup.sh + systemd + guide)

## Hors périmètre V1
- Retry automatique des posts échoués (V2)
- Analytics/perf des posts publiés (V2 — alimentera l'apprentissage du Policy)
- Multi-comptes / multi-marques
- Tournoi multi-vidéos (mécanique TOURNOI du dossier)
