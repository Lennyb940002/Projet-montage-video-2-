# Publication Instagram (full API, immédiate) — Design

**Date :** 2026-06-07
**Statut :** Design validé
**Contexte :** Sous-système B de AutoMontage. Publier une vidéo (Reel) sur Instagram via l'API officielle Meta Graph, **publication immédiate** (la programmation et TikTok viendront après).

## Décisions validées
- **API officielle Meta Graph** (Instagram Content Publishing), usage **mode Développement** sur le **propre compte** de l'utilisateur (pas d'App Review nécessaire pour soi-même).
- **URL publique** de la vidéo via **tunnel cloudflared temporaire** (sert le fichier depuis le PC, referme après).
- **Publication immédiate** d'abord (scheduling = phase ultérieure).
- Identifiants (**token longue durée** + **IG Business Account ID**) saisis par l'utilisateur, stockés hors code.

## Prérequis utilisateur (manuels, guidés)
Compte IG Business/Creator lié à une page FB ; app Meta (Instagram Graph API) ; token longue durée (scopes `instagram_basic`, `instagram_content_publish`, `pages_show_list`) ; IG Business Account ID. App laissée en mode Développement.

## Architecture (code)

- **`backend/settings.py`** : lecture/écriture de `~/.automontage/settings.json`
  (`ig_token`, `ig_user_id`). Ne jamais committer ces valeurs.
- **`backend/pipeline/tunnel.py`** :
  - `serve_file(path)` : lance un serveur HTTP local (thread) servant le dossier du fichier.
  - `quick_tunnel(port)` : lance `cloudflared tunnel --url http://127.0.0.1:PORT`,
    parse l'URL `https://*.trycloudflare.com` sur la sortie, la renvoie.
  - `public_url(video_path)` : context manager → `(url_du_fichier)` ; ferme serveur+tunnel à la sortie.
  - localisation de `cloudflared.exe` (téléchargé une fois si absent).
- **`backend/pipeline/publish_ig.py`** :
  - `create_container(ig_user_id, video_url, caption, token)` → `creation_id`.
  - `wait_ready(creation_id, token, timeout=120)` → poll `status_code` jusqu'à `FINISHED`
    (erreur si `ERROR`/timeout).
  - `publish(ig_user_id, creation_id, token)` → `{id, permalink?}`.
  - `publish_reel(video_path, caption, token, ig_user_id)` → orchestre tunnel + les 3 étapes.
  - API : `https://graph.facebook.com/v21.0`. Erreurs Meta remontées lisibles ; limite 25/j signalée.
- **`backend/service.py`** : `publish_instagram(video_path, caption)` lit les settings, appelle `publish_reel`.
- **`backend/server.py`** :
  - `GET /settings` → `{ig_user_id, has_token}` (jamais renvoyer le token en clair).
  - `POST /settings {ig_token, ig_user_id}` → sauvegarde.
  - `POST /publish/instagram {video_path, caption}` → `{id}` ou `{error}`.
- **Frontend** :
  - Panneau **Réglages** (champ token + IG ID, bouton Enregistrer).
  - Bouton **« Publier sur Instagram »** (actif après export ; envoie la vidéo exportée + la description courante).
  - Retour d'état : « Tunnel… → Encodage Meta… → Publié ✅ (lien) » ou erreur claire.

## Flux
Exporter la vidéo → Publier sur Instagram → ouvre tunnel (URL https) → crée container → attend l'encodage (polling) → publie → ferme tunnel → affiche le lien du post.

## Erreurs & tests
- **Erreurs** : token absent/invalide → message clair ; cloudflared absent → instruction ; encodage `ERROR`/timeout → message ; quota 25/j atteint → message.
- **Tests (hors-ligne)** :
  - `publish_ig` avec un **faux serveur Graph** (monkeypatch httpx) : séquence container→poll(FINISHED)→publish ; gère `status_code=ERROR`.
  - `tunnel.serve_file` : le fichier est bien servi en local (GET renvoie les octets) — sans cloudflared.
  - `settings` : write puis read round-trip.
- Le test **réel** (vraie publication) se fait manuellement une fois le token configuré.

## Hors périmètre
Programmation à heure future · TikTok · publication pour des comptes tiers (App Review) · stories/feed (on fait Reels).
