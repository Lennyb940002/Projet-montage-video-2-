# Auto-post vacances via GitHub Actions

Le stock (`stock/*.mp4` + `stock/planning.json`) est pré-généré. GitHub Actions
poste chaque reel à son créneau, tout seul, PC éteint. Voici les étapes **à faire
une fois, depuis le PC de bureau, avant de partir**.

## 1. Pousser le repo (avec le stock)

```bash
cd C:\Users\User\Desktop\auto-montage
git push -u origin main
```

> ~232 Mo de vidéos → le push prend quelques minutes. Une fenêtre de login GitHub
> s'ouvre (pas de mot de passe à me donner). Repo **privé** confirmé.

## 2. Configurer les 2 secrets (obligatoire)

Sur GitHub : **repo → Settings → Secrets and variables → Actions → New repository secret**.
Créer exactement ces deux secrets :

| Nom | Valeur (à copier depuis `~/.automontage/settings.json` sur le PC) |
|-----|------------------------------------------------------------------|
| `UPLOAD_POST_TOKEN` | champ `uploadpost_token` |
| `UPLOAD_POST_USER`  | champ `uploadpost_user` (ex : `Flowers`) |

> ⚠️ Ne jamais coller ces valeurs ailleurs que dans les GitHub Secrets. Le code
> ne les contient pas.

## 3. Vérifier que Actions est activé

**repo → Actions** : si un bandeau demande d'activer les workflows, cliquer
« I understand… enable ». Le workflow `post-stock` apparaît.

## 4. Reconnecter TikTok (sinon seul Instagram partira)

Sur **upload-post.com → comptes connectés → reconnecter TikTok**. (Tu avais
révoqué l'accès pendant la détox.) Instagram, lui, part sans rien faire.

## 5. (Si besoin) Ajuster la date de début

Le planning va du **2026-07-07 au 2026-07-20**. Si tes vacances commencent un
autre jour, décale sans rien re-générer :

```bash
python deploy/shift_planning.py 2026-07-12   # nouvelle date de début
git add stock/planning.json && git commit -m "chore: decale planning" && git push
```

## 6. Tester tout de suite (recommandé)

**repo → Actions → post-stock → Run workflow** (bouton manuel). Ça poste au plus
2 reels dus. Vérifie sur Instagram que le post arrive. Regarde le log du run en
cas d'échec (souvent = secret manquant ou TikTok non reconnecté).

## Comment ça marche

- Cron **toutes les 30 min** (`.github/workflows/post_stock.yml`). GitHub est
  best-effort : léger retard possible, sans gravité.
- `deploy/post_from_planning.py` lit `planning.json`, poste les reels **dus**
  (date/heure Europe/Paris ≤ maintenant, non postés), coche `posted: true`,
  re-commit le planning. **Max 2 posts par run** (anti-flood, rattrapage lissé).
- Quota Actions (repo privé) : ~700 min sur 2 semaines, dans le gratuit (2000/mois).

## Limites honnêtes

- Banque de **26 clips vidéo** → sur 70 reels, les mêmes montres reviennent
  (anti-répétition seulement *rapprochée*). Normal, pas un bug.
- Prix « devine le prix » = **194,90 €** (celui des tuiles). Change la constante
  `PRIX` dans `deploy/generate_stock.py` si besoin, puis régénère.
- Le reveal/CTA ne sont pas encore des écrans animés (montage rythmé = phase
  ultérieure). Contenu **brut mais publiable**.
