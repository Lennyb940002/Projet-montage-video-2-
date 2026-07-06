# Reels Flowers Chrome — Refonte contenu (Phase 0 + 1A)

Date : 2026-07-05
Statut : design validé (direction), en attente de review du spec
Branche : `boost-hook`

## 0. Objectif

Faire que les reels du moteur silencieux ne tournent **plus que sur le nouveau
guide créatif** (identité / psychologie / perception), et **supprimer tout le
contenu générique ancien**. On vise un MVP opérationnel rapide : relancer une
production qui ne ressemble plus aux anciens reels.

Périmètre de CE spec : **Phase 0 (sécurisation) + Phase 1A (5 formats)**.
Hors périmètre (phases ultérieures, specs séparés) : formats 1B (projection,
vibe, style, quel-homme, mood, red/green flag), Fiche d'identité (Phase 2),
Budget flash + SFX (Phase 3), montage rythmé multi-écrans (Phase 4).

## 1. Découverte structurante

Les 5 formats de la Phase 1A partagent **le même squelette** : 3 montres
empilées (`split_3`). Ils ne diffèrent que par (a) le hook et (b) le **type de
label** affiché sous chaque montre. Conséquence : **aucun nouveau renderer** en
Phase 1A — uniquement de la couche contenu + un branchement propre des labels.

## 2. Phase 0 — sécurisation

1. Git vérifié : repo présent, branche `boost-hook`. Suppression réversible.
2. Dans `config.py`, `mechanic_bias` → **0** pour toutes les mécaniques bannies :
   `comparison`, `vote`, `elimination`, `top3`, `battle`, `transformation`,
   `erreur`, `pov`, `collection`, `comparison_4`, `collection_4`, `revelation`
   (reveal-suspense « regarde jusqu'au bout »).
   Un biais 0 retire la mécanique de la rotation (policy.py:79). L'ancien style
   ne peut plus sortir. Aucune suppression de fichier en Phase 0 : les hook
   JSON obsolètes seront supprimés en fin de 1A une fois le remplacement vérifié.

## 3. Phase 1A — les 5 formats

| Format guide | Mécanique | asset_count | layout | label_mode |
|---|---|---|---|---|
| Choisis une montre, je te dis qui tu es | `test` (conservée) | 3 | split_3 | `profile` |
| La montre que tu choisis révèle quelque chose | `revelation_psy` (neuf) | 3 | split_3 | `psycho` |
| Ton choix te trahit | `trahison` (neuf) | 3 | split_3 | `trahison` |
| Ce que ta montre dit aux autres | `perception` (neuf) | 3 | split_3 | `perception` |
| Test rapide / choisis une montre | `test_perso` (neuf) | 3 | split_3 | `test_reveal` |

Toutes en `goal="engagement"`, `default_duration` 6.0. Biais (mix section 20,
ramené aux 5 formats 1A) : `test` 3.0, `revelation_psy` 2.5, `trahison` 2.0,
`perception` 1.5, `test_perso` 1.0.

## 4. Couche contenu

Nouveau module `backend/silent/content.py` + dossier `backend/silent/banks/` :

- `hooks_test.json`, `hooks_revelation_psy.json`, `hooks_trahison.json`,
  `hooks_perception.json`, `hooks_test_perso.json` — chaque entrée `{text, angle}`.
- `cta.json` — CTA en rotation, typés `comment | dm | question` [section 26].
- `familles.json` — cœur du système (voir §4.1).

### 4.1 Structure de `familles.json` (ajustements 1 + 3)

Mapping **dossier montre → famille**. Familles : GMT/Batman, Daytona/Chrono,
Or rose, Full black, Acier/Silver, Bleu/Saphir, Rouge/Ruby.

Pour **chaque famille**, et pour **chaque `label_mode`** (`profile`, `psycho`,
`trahison`, `perception`, `test_reveal`), trois listes de labels :

```json
"gmt": {
  "dossiers": ["Seiko GMT"],
  "labels": {
    "profile":    { "coherents": ["discret","stratégique","froid","carré"],
                    "surprise_acceptes": ["ambitieux discret","indépendant calme"],
                    "interdits": ["solaire","extravagant","joyeux","fun"] },
    "psycho":     { "coherents": ["tu contrôles ton image"],
                    "surprise_acceptes": ["tu caches un côté compétiteur"],
                    "interdits": ["tu veux qu'on te remarque tout de suite"] },
    "trahison":   { ... }, "perception": { ... }, "test_reveal": { ... }
  }
}
```

Une GMT a donc des **phrases psycho, perceptions, trahisons** cohérentes — pas
seulement des adjectifs. Chaque famille couvre les 5 `label_mode`.

`content.py` expose `pick_labels(mechanic, assets, rng)` → tuple de labels
`[(texte, couleur)]`, un par montre, avec **mix 80/20 crédible** :
- 80 % (**coherent**) : tirage dans `coherents` de la famille pour le `label_mode`.
- 20 % (**surprise**) : tirage dans `surprise_acceptes` **uniquement** — jamais
  dans une autre banque, **jamais** dans `interdits`. Surprise = crédible, pas
  aléatoire.
Le choix 80/20 et le tirage sont seedés (déterministes via `rng`). `pick_labels`
retourne aussi, par montre, le **mode utilisé** (`coherent`/`surprise`) et la
**famille détectée**, pour le manifest.

### 4.2 CTA (ajustement 4)

`content.pick_cta(mechanic, rng, history)` tire un CTA typé en rotation
(`comment`/`dm`/`question`) et le pose dans `recipe.cta_type` + texte. Le CTA est
**toujours généré et logué au manifest** (audit de rotation). Affichage visuel :
si trivial, un écran/bandeau CTA final simple ; sinon reporté (non bloquant 1A).

## 5. Changement d'architecture (le seul code non-trivial)

Aujourd'hui les profils sont **hardcodés** dans `render._cell_labels`
(`MINIMALISTE/AMBITIEUX/CLASSIQUE/AUDACIEUX`). On les sort du renderer :

1. `recipe.py` : ajouter `labels: tuple = None` au `VideoRecipe` (rétro-compat).
2. `policy.py` : après le tirage des assets, appeler
   `content.pick_labels(mechanic, assets, rng)` et passer le résultat au recipe.
3. `render.py` : `_cell_labels(recipe)` retourne `recipe.labels` s'il est
   défini. **Fail dur (ajustement 2)** : si `recipe.mechanic` ∈
   {`test`, `revelation_psy`, `trahison`, `perception`, `test_perso`} et
   `recipe.labels` est `None` → `ValueError` explicite. Le fallback hardcodé
   (`MINIMALISTE/AMBITIEUX/CLASSIQUE/AUDACIEUX`) ne reste **que** pour les
   mécaniques hors-1A ; il ne peut plus jamais ressortir sur un format 1A par
   accident. Aucune décision dans le renderer → invariant « renderer =
   exécution pure » respecté.

## 6. Anti-répétition (section 25) — dès 1A

- **Trio de montres jamais identique** : `exclude_models` (déjà supporté par le
  sampler) alimenté par les N dernières vidéos.
- **Hook ≤ 2 fois / 10** et **profils/labels jamais répétés à l'identique** :
  le store logue désormais `assets`, `hook`, `labels` ; policy lit l'historique
  enrichi et pénalise (soft score) les répétitions.
- **Montre voyante pas toujours en n°2** : ordre des assets mélangé (seedé)
  après tirage, sans position fixe pour une famille donnée.
- **CTA en rotation** commentaire / DM / question : `cta.json` typé, rotation
  seedée sur l'historique.

## 7. Livrable 1A

Script `deploy/generate_batch_1a.py` : génère un lot de **30 reels** —
10 `test`, 8 `revelation_psy`, 6 `trahison`, 4 `perception`, 2 `test_perso` —
dans `output/batch_1a/` (**revue manuelle**, PAS de post auto).

**Manifest JSON (ajustement 5)** — par reel, champs obligatoires :
`mecanique`, `hook`, `montres` (chemins), `familles_detectees` (par montre),
`labels` (par montre), `cta` (texte + type), `mode_coherence` (par montre :
`coherent` | `surprise`), `chemin_export`. But : audit rapide du respect du guide
(rotation CTA, variété labels, crédibilité surprises).

## 8. Fichiers touchés

- `backend/config.py` — biais (Phase 0) + déclaration banques.
- `backend/silent/registry.py` — +4 mécaniques 1A.
- `backend/silent/recipe.py` — champ `labels`.
- `backend/silent/policy.py` — décide labels + anti-répétition enrichie.
- `backend/silent/render.py` — lit `recipe.labels`.
- `backend/silent/content.py` (neuf) + `backend/silent/banks/*.json` (neuf).
- store silencieux — log enrichi (assets/hook/labels).
- `deploy/generate_batch_1a.py` (neuf).
- tests : `test_silent_registry`, `test_silent_policy`, + neuf `test_content_banks`.

## 9. Critères de validation (avant export d'un reel — section 30)

Hook lisible <1s ; montre visible ; identité/vibe présente ; CTA simple ;
pas de formulation risquée ; <9s ; donne envie de choisir. Un reel qui ne
respecte pas est écarté du lot.

## 10. Ce qui reste explicitement pour plus tard

- Formats 1B, Fiche d'identité, Budget flash + SFX, montage rythmé.
- Reconnexion TikTok sur upload-post (action propriétaire, hors code).
