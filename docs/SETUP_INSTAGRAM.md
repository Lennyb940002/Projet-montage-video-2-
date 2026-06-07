# Guide : connecter l'app à Instagram (à faire une fois)

But : obtenir 2 valeurs à coller dans l'app → **un token longue durée** et ton **IG Business Account ID**.
L'app reste en "mode Développement" → tu publies sur **TON compte** sans validation Meta.

## 1. Passer Instagram en compte pro
- App Instagram → Paramètres → Compte → **Passer à un compte professionnel** (Créateur ou Entreprise).

## 2. Lier une page Facebook
- Crée (ou utilise) une **page Facebook**.
- Dans Instagram → Paramètres → **Comptes liés / Partage sur d'autres apps** → lie la page Facebook.
  (ou depuis la page FB → Paramètres → Comptes liés → Instagram.)

## 3. Créer une app Meta
- Va sur https://developers.facebook.com/ → connecte-toi → **Mes apps** → **Créer une app**.
- Type : **Entreprise** (Business).
- Dans l'app, ajoute le produit **Instagram** → **Instagram Graph API** (ou "Instagram" / "API Graph").

## 4. Générer un token + récupérer l'ID
Le plus simple : **Outil Explorateur d'API Graph** (Graph API Explorer)
- https://developers.facebook.com/tools/explorer/
- Sélectionne ton app en haut.
- "Generate Access Token" / ajoute les **permissions** :
  - `instagram_basic`
  - `instagram_content_publish`
  - `pages_show_list`
  - `pages_read_engagement`
  - `business_management`
- Génère le token, autorise avec ton compte.

**Récupérer l'IG Business Account ID** (dans l'Explorateur, fais ces requêtes GET) :
1. `me/accounts` → note l'`id` de ta **page Facebook**.
2. `{PAGE_ID}?fields=instagram_business_account` → renvoie ton **IG Business Account ID** (c'est CETTE valeur qu'il faut).

**Token longue durée (~60 jours)** : le token de l'Explorateur est court (1-2h). Pour le rallonger :
- GET `oauth/access_token?grant_type=fb_exchange_token&client_id={APP_ID}&client_secret={APP_SECRET}&fb_exchange_token={TOKEN_COURT}`
- (APP_ID / APP_SECRET = dans Paramètres → Général de ton app.)
- Le résultat = ton **token longue durée** → c'est celui à coller dans l'app.

## 5. Coller dans l'app
- Ouvre AutoMontage → **Réglages** → colle le **token longue durée** + l'**IG Business Account ID** → Enregistrer.

## Notes
- Tant que l'app Meta est en "Développement", tu publies sur ton propre compte (toi = admin). OK pour usage perso.
- Le token longue durée expire ~60 jours → il faudra le régénérer (l'app préviendra si erreur d'auth).
- Limite Meta : ~25 publications/jour.
