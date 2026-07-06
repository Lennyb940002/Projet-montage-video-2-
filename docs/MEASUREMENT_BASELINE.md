# Baseline de mesure — Flowers Chrome (GELÉE le 2026-06-23)

But : garantir la **comparabilité statistique** du dataset. On ne mesure pas un
système qui bouge ; on mesure une **réponse** à des **conditions d'entrée fixes**.

> Règle d'or : **« stabiliser les conditions de mesure », pas « le système ».**
> Si on change une variable ci-dessous → la fenêtre d'observation est **remise à zéro**.

## Fenêtre d'observation
- Début : **2026-06-23**
- Fin (mini) : **~2026-07-07** (10-14 jours)
- Condition de validité : **même distribution d'entrée + même cadence + même mix de formats** sur toute la fenêtre.

## Variables GELÉES (ne pas toucher pendant la fenêtre)
**Mix vidéo** (`SILENT['mechanic_bias']`) — **60 / 20 / 15 / 5** :
- identité (`test`) 6.0 · élimination 2.0 · projection 1.5 · duel (`vote`) 0.5 · rétention (`revelation`) 1.0
- bannis (0) : collection, top3, comparison, comparison_4, battle, pov, erreur, transformation

**Hooks par famille** (gelés) : identité = 10, élimination = 6, projection = 5
*(fichiers `backend/silent/hooks/test|elimination|projection.json`)*

**Cadence** (gelée) :
- Vidéos : 7h00 · 11h30 · 15h00 · 17h00 · 21h00 (21h = rétention)
- Carrousels : 12h00 (valeur) · 18h00 (objection)
- Story de partage : 1 par carrousel

**Mix de formats** (gelé) : 5 vidéos + 2 carrousels + 2 stories / jour
**Coloris** : rotation noir / blanc (rose retiré)
**CTA** : code `FCxxx` unique par carrousel

## Population de contenu (GELÉE) — la variable invisible
Empreinte figée le 2026-06-23 (`backend/posts/baseline.py`, `~/.automontage/baseline.json`) :
- **13 clips** : GMT 3 · Or rose 3 · Saphir 3 · Silver 3 · **Ruby 1**
- ⚠️ **Distribution NON uniforme** (Ruby sous-exposé) → toute lecture par montre doit
  être **normalisée par exposition**, sinon on mesure la composition du catalogue, pas l'effet.

**Changement invisible = reset.** Toute modif non déclarée de la banque (montre ajoutée,
clip remplacé, qualité visuelle différente) casse la comparabilité sans casser le système.
→ Détecteur automatique : `python -m backend.posts.baseline --check` (à lancer régulièrement ;
s'il signale une dérive → la fenêtre repart à zéro).

## Ce qu'on observe (NE rien conclure avant la fin de fenêtre)
1. Les mêmes hooks dominent-ils toujours ? (PAR HOOK)
2. « Identité » reste stable ou se fragmente ? (famille × hook)
3. Un seul modèle tire-t-il les DM ? (PAR MONTRE × dm)
4. Les DM suivent-ils les vues ou les commentaires ?
5. Un format = un type de conversion ? (famille × dm_rate)

## Prérequis n°1 à la validité : continuité temporelle
Le PC qui s'endort = **trous dans le dataset** = échantillon instable.
→ **Déploiement Oracle prioritaire** (raison : stabilité temporelle du dataset, pas confort).

## Après la fenêtre (Phase 3 — seulement si signal propre)
Définir des **règles de décision automatiques** : quel hook monter à 70 %, quel
format supprimer, quel modèle scaler. **Pas avant** un dataset propre et comparable.
