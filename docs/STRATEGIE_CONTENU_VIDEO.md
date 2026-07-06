# Stratégie de contenu vidéo — Flowers Chrome (v1, 22/06/2026)

Issue de l'analyse des 1res perfs (cf `RAPPORT_PERFS_VIDEOS_2026-06-22.md`).
Encodée dans le moteur via `SILENT['mechanic_bias']` (poids par mécanique) +
les hooks JSON (`backend/silent/hooks/`).

## 🎯 MIX VIDÉO CIBLE : 60 % identité · 20 % décision forcée · 15 % projection · 5 % duel
(biais `test`=6.0 / `elimination`=2.0 / `projection`=1.5 / `vote`=0.5 ; top3/classement/collection retirés)

## 🥇 MOTEUR DOMINANT (60 %) — IDENTITÉ  *(confirmé data : x3-x5 vues)*
« Ce que ton choix dit de toi » = 881 vues / 595 reach, vs 170-310 pour le reste.
Le spectateur ne voit plus une montre, il se voit lui-même (même ressort que
« Quel personnage es-tu ? »). → mécanique `test` (biais 5.0 ≈ 46-50 % du contenu).
Famille de hooks (`backend/silent/hooks/test.json`) : ce que ton choix dit de toi,
quel homme es-tu, ton style selon ton choix, ton niveau d'élégance, ta personnalité
horlogère, la montre que tu choisis révèle quelque chose, ce que tu recherches dans
la vie, ton alter ego, choisis sans réfléchir, quel est ton profil.

## ✅ Priorité (poids élevé)
- **Décision forcée** (`elimination`) + **Projection / occasion** (`projection`).
- **Duel** (`vote`) = repassé en **remplissage** (faible fréquence, plus banni) :
  « qui mérite de gagner ? », « le gagnant selon vous ? » fonctionnent mais ne
  surperforment pas.
- **Décision forcée** — « Une seule survit », « Tu ne peux en garder qu'une »,
  « Choix impossible », « Si je devais faire le ménage aujourd'hui ».
  → mécanique `elimination` (3 montres).
- **Projection / occasion** — « Laquelle pour un mariage ? », « pour l'été ? »,
  « pour partir en vacances ? », « pour un premier rendez-vous ? ».
  → mécanique `projection` (2 montres). *(nouvelle)*

## ⚠️ À réduire fortement (poids faible)
- **Vote classique** — « Votez pour votre favorite », « Qui mérite de gagner ? ».
  Mieux que la comparaison pure, mais pas ce qui ressort le plus.
- **Classement / Top 3** — « Classement du jour ». Manque d'autorité pour l'instant.

## ❌ Bannis (poids 0 — retirés de la rotation)
- **Comparaison générique** — « Laquelle choisissez-vous ? », « A ou B ? ».
  Aucun enjeu émotionnel (160 vues, 1 like).
- **Hooks techniques** — « GMT vs… », « Saphir vs Minéral ». Parle aux passionnés,
  pas aux 95 % de TikTok/Reels. (mécanique `battle`)
- **POV hors-univers** — « POV ton salaire vient de tomber ». Template générique
  recyclé, ne construit pas l'identité du compte (56 vues).
- **Grille 4 montres** — disperse le choix.

## À faire ensuite (pas encore codé)
- **CTA commentaire chiffré** systématique (« Commente 1 ou 2 ») — 0 commentaire
  sur toutes les vidéos jusqu'ici.
- Soigner la **1re seconde** (abandon 47-70 %).
- (Marque) masquer les noms de luxe dans les captions (« Daytona » → périphrase).

## Plan d'évolution (copywriter, 22/06) — à wirer
*(Story sondage 20h ABANDONNÉE — sticker sondage cliquable impossible via API.)*
1. **Carrousels = 12h VALEUR / 18h OBJECTION D'ACHAT** (« pourquoi 199 € ? »,
   « comment reconnaître une vraie ? », « quelle taille ? ») → 2 pools de sujets,
   routage par créneau. (à wirer avec le scheduler carrousels + clé Gemini)
2. **1 contenu DM-first / jour** (« Choisis une montre, DM-moi, je te dis ce que ça
   révèle » / « DM CATALOGUE ») → famille de hooks + CTA DM explicite.
3. **Surveillance** : si identité reste x2-x4, monter à **70-80 %** des vidéos.
