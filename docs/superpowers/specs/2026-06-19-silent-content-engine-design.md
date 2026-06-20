# Silent Content Engine — Design (V1)

**Date :** 2026-06-19
**Statut :** Design validé (en attente de revue finale avant plan d'implémentation)
**Contexte :** Le produit actuel transforme une voix-off en montage vertical. On ajoute un
**second pipeline indépendant** : générer automatiquement des vidéos courtes 9:16 **sans voix-off**,
à partir de clips/images de montres + texte à l'écran. Objectif produit : une **machine à
permutations contrôlées** capable de produire 100 vidéos uniques **sans collision perceptuelle** —
PAS un optimiseur de performance TikTok (ça viendra en V4/V5).

---

## 1. Objectif et cadrage

Prendre des clips de montres et produire des MP4 1080×1920 (3–8 s) automatiquement, reposant
uniquement sur : images/clips + texte à l'écran + transitions (musique optionnelle, hors V1).

**Principe directeur (séquençage industriel) :** on sépare strictement
- **(A) stabilité de production** — générer en volume, fiable, varié — *c'est V1*
- **(B) optimisation future** — apprendre ce qui performe — *V4/V5, hors scope*

On n'introduit AUCUN des éléments de (B) en V1 : pas de performance score, pas de learning loop,
pas d'asset intelligence, pas de prix, pas de tags.

### Scope V1 — 3 mécaniques, taggées par `goal`
| Mécanique | `goal` | Layout | Assets |
|---|---|---|---|
| COMPARAISON | engagement | `split_2` | 2 |
| VOTE | engagement | `split_2` | 2 |
| REVELATION | retention | `reveal` | 1 |

Le tag `goal` est présent **dès V1** (mécanisme d'isolation analytique futur) mais n'est PAS une
séparation par version. Roadmap d'extension : **V1.1** TOP3 + COLLECTION (layouts `top3`, `grid_4`),
**V1.2** ELIMINATION + POV (layouts `grid_4`, `single`).

---

## 2. Architecture — 3 couches strictement séparées

```
ContentStrategy        intention      {goal, count, mechanic?}
      ↓
Policy Engine    ★ LE CŒUR  →  décide (rules + fatigue + contraintes)
      ↓
VideoRecipe          structure IMMUABLE
      ↓
Renderer             exécution pure  → MP4
      ↓
DB logging           (alimente l'historique relu par le Policy)
```

**Invariant architectural global (le plus important) :** le **Policy Engine est le SEUL système
de décision**. Décision interdite dans `renderer`, `recipe`, `hooks`, `store`. Toute violation
casse la modularité.

**Double rôle du Policy Engine (à nommer explicitement) :**
1. **Constraint solver + stochastic sampler** — résout les contraintes (goal, registry, validité)
   et tire une décision pondérée dans l'espace créatif borné.
2. **Sequence stabilizer** — garantit la **cohérence temporelle de la séquence générée** (la
   diversité D1-D4 n'a de sens qu'à l'échelle de la séquence, pas d'une vidéo isolée). Ce rôle est
   formalisé par l'invariant **D0** ci-dessous.

Résumé conceptuel du Policy Engine : *a deterministic probabilistic constraint solver over a
bounded creative space, acting as a sequence stabilizer.*

---

## 3. Structures de données

### ContentStrategy (intention)
```python
{
  "goal":     "engagement" | "retention",   # obligatoire
  "count":    int,                           # nb de recipes à produire
  "mechanic": str | None,                    # override optionnel d'une mécanique précise
  "assets":   list[str] | None,              # assets imposés (pick manuel UI) ; None => Policy choisit
}
```
**Frontière de sélection des assets (Option C — hybride) :** la responsabilité est découpée en 3
étages pour garder le Policy purement décisionnel ET permettre un sampling testable/scalable :
```
Policy   → émet des CONTRAINTES d'assets   {count, filters}   (décision)
Sampler  → réalise le SAMPLING effectif depuis la banque (seedé)   (mécanique, dans registry/asset_pool)
Recipe   → BINDING final immuable des assets choisis   (structure gelée)
```
- Si `strategy.assets` est fourni (pick manuel UI) → c'est une contrainte forte : le Sampler le
  renvoie tel quel après vérif `len == asset_count[mechanic]` (I4 : lecture seule).
- Si `None` → le Policy émet `{count: asset_count[mechanic], filters: {}}` (V1 : pas de filtre
  tags ; V2 ajoutera les filtres) et le Sampler tire `count` assets seedés depuis la banque.
- Dans tous les cas le **Policy reste seul décideur** (il fixe les contraintes), le Sampler
  n'invente rien, et la Recipe fige le binding (I1).

### VideoRecipe (sortie immuable — IR de production vidéo)
```python
@dataclass(frozen=True)
class VideoRecipe:
    mechanic: str          # ∈ registry.mechanics
    layout: str            # ∈ registry.layouts[mechanic]
    hook: str              # texte affiché
    content_angle: str     # angle catégoriel du hook (analytics-ready)
    assets: tuple[str]     # chemins ; len == registry.asset_count[mechanic]
    duration: float        # ∈ [min_duration, max_duration]
    font: str              # variation seedée (aplati en champs scalaires immuables
    accent: str            #   plutôt qu'un dict, pour rester strictement frozen)
    text_anim: str         #   "fade" | "pop"
    seed: int
```
Tout converge vers cet objet ; **tout le reste n'est que compilation**. Une fois émis, il est
**gelé** (frozen) : pas de patch post-render, toute adaptation = nouvelle invocation du Policy.

### Registry (data-driven)
```python
MECHANICS = {
  "comparison": {"goal": "engagement", "asset_count": 2,
                 "layouts": ["split_2"], "hook_file": "comparison.json",
                 "default_duration": 6.0},
  "vote":       {"goal": "engagement", "asset_count": 2,
                 "layouts": ["split_2"], "hook_file": "vote.json",
                 "default_duration": 6.0},
  "revelation": {"goal": "retention",  "asset_count": 1,
                 "layouts": ["reveal"], "hook_file": "revelation.json",
                 "default_duration": 5.0},
}
LAYOUTS = {"split_2": {...geometry...}, "reveal": {...geometry...}}
```

### Hooks — sous-système orthogonal (latent engagement layer)
Les hooks sont indépendants de la mécanique ET du layout (variable d'engagement orthogonale).
Un fichier par mécanique, chaque hook porte son **angle** :
```json
// backend/silent/hooks/comparison.json
[ {"text": "Laquelle tu choisis ?", "angle": "which_choose"},
  {"text": "A ou B ?",             "angle": "a_or_b"},
  {"text": "Une seule à garder",   "angle": "keep_one"},
  {"text": "Votez en commentaire", "angle": "vote_cta"} ]
```
`content_angle` est stocké en DB → A/B testing implicite futur sans refonte (ex : découvrir que
"keep_one" fait 2,3× plus de commentaires que "which_choose").

---

## 4. Policy Engine — invariants (contrat V1)

**Rôle :** fonction pure `PolicyEngine(strategy, history, registry, rng_seed) → VideoRecipe`.
Déterministe conditionnel (seed + state), sans effet de bord, sans métrique externe (V1),
seul responsable du choix final.

### 4.1 Invariants structurels (non négociables)
- **I1 — Immutabilité de sortie.** Un VideoRecipe émis est immuable. Pas de patch post-render,
  pas de correction dynamique ; toute adaptation = nouvelle invocation.
- **I2 — Validité strictement typée.** `mechanic ∈ registry.mechanics` ; `layout ∈
  registry.layouts[mechanic]` ; `hook ∈ hooks[mechanic]` ; `len(assets) == asset_count[mechanic]` ;
  `duration ∈ [min_duration, max_duration]`. Échec → rejet immédiat (pas de fallback silencieux).
- **I3 — Cohérence mécanique → layout.** `∀ recipe: layout ∈ ALLOWED_LAYOUTS(mechanic)`.
  Interdit : cross-layout fallback, layout random indépendant de la mécanique.
- **I4 — Séparation Strategy → Recipe.** Le Policy ne mute JAMAIS la ContentStrategy. Il la lit,
  la satisfait, la traduit ; jamais la compléter/réinterpréter hors scope.

### 4.2 Invariants de diversité (anti-répétition)
- **D0 — Cohérence temporelle de séquence (sequence stabilizer).** Le Policy garantit la cohérence
  de la **séquence** générée, pas seulement de chaque vidéo isolée. Les biais D1-D4 opèrent sur la
  fenêtre glissante d'historique, jamais sur un seul point. C'est le second rôle nommé du Policy.
- **D1 — Pas de répétition immédiate forte.** `mecanique(t) ≠ mecanique(t-1)` avec proba ≈ 1
  (soft constraint via `repetition_bias`, PAS d'exclusion dure).
- **D2 — Anti-pattern ABAB.** Interdiction des cycles de longueur ≤ 2 : si le choix de `m`
  formerait/prolongerait une alternance courte → `pattern_penalty`.
- **D3 — Fenêtre de diversité glissante.** Sur les N=5 dernières vidéos : pas plus de ~60–70 %
  d'une seule mécanique. Biais fort, pas blocage.
- **D4 — Hook diversity indépendante.** `hook_type(t)` varie indépendamment de `mechanic(t)` :
  même mécanique ≠ même hook systématique (espace orthogonal).

### 4.3 Invariants de sélection (Policy core)
- **S1 — Sélection probabiliste pondérée OBLIGATOIRE.** Interdits : `argmax`, random pur sans
  biais, sélection déterministe fixe.
- **S2 — Normalisation softmax.** `weights = softmax(score / temperature)`, température fixée en
  V1 (pas de tuning dynamique).
- **S3 — Reproductibilité par seed.** Même `(strategy, history, seed)` → même recipe. History
  snapshotée.

### 4.4 Invariants temporels
- **T1 — History = snapshot read-only** pendant l'exécution (pas d'append, pas de lecture
  partielle instable, pas de race condition).
- **T2 — Sliding window only.** Le Policy ne voit que les N dernières vidéos (N fixe), pas
  l'historique complet ni filtré dynamiquement.
- **T3 — Stateless.** Chaque appel = fonction pure, aucune mémoire interne persistante ; toute
  mémoire est externalisée dans `store.py`.

### 4.5 Invariants de cohérence produit
- **P1 — `strategy.goal` mappe vers ≥ 1 mécanique valide**, sinon erreur explicite (pas de
  fallback implicite).
- **P2 — Pas de mécanique hors registry** (pas d'innovation spontanée, pas d'injection de type).
- **P3 — Respect du budget** : `strategy.count == nombre de recipes générés` (ni
  sur-génération, ni sous-production silencieuse).

### 4.6 Invariants de robustesse
- **R1 — No silent fallback** : état invalide → erreur explicite, pas de substitution cachée.
- **R2 — Fail fast** : échec si registry incohérent, hooks manquants, layouts invalides.
- **R3 — Validation avant émission** : `validate(recipe)` DOIT passer avant `return`.

---

## 5. Algorithme de sélection (formalisation de la fatigue)

```
candidates = [m for m in registry.mechanics
              if registry[m].goal == strategy.goal]          # P1: non vide sinon erreur
if strategy.mechanic is not None:
    candidates = [strategy.mechanic]                          # override explicite (I4: lecture seule)

for m in candidates:
    score(m) = BASE
             - W_REP * occurrences(m, history[-5:]) / 5       # D1, D3
             - W_PAT * is_short_cycle(m, history[-2:])        # D2 (ABAB)
weights = softmax(score / TEMPERATURE)                        # S2
mechanic = weighted_random(candidates, weights, rng)          # S1, S3 (seedé)

layout       = pick(registry[mechanic].layouts, rng)          # I3
hook, angle  = pick_hook(mechanic, rng)                       # D4 orthogonal
# Assets — Option C : Policy émet la contrainte, le Sampler réalise le tirage, Recipe fige.
constraint   = {"count": registry[mechanic].asset_count, "filters": {}}  # V1: pas de filtre tags
assets       = strategy.assets or sampler.sample(constraint, rng)        # mécanique, pas décision
assert len(assets) == registry[mechanic].asset_count          # I2
variation    = pick_variation(rng)                            # font/accent/anim
duration     = clamp(registry[mechanic].default_duration, MIN, MAX)
recipe       = VideoRecipe(... frozen ...)
validate(recipe)                                              # R3, I2
return recipe
```

Constantes V1 dans `config` (ajustables) : `W_REP`, `W_PAT`, `TEMPERATURE`, `WINDOW_N=5`,
`MIN_DURATION=3.0`, `MAX_DURATION=8.0`.

**Edge case acté :** avec exactement 3 mécaniques, le soft scoring (jamais 0 absolu) garantit
qu'au moins une mécanique reste tirable → pas de pool vide, pas de cycle déterministe `COMP→VOTE
→REVEAL→COMP...`. Le biais pousse vers la variété sans interdire.

---

## 6. Layouts V1 (rendu ffmpeg, exécution pure)

- **`split_2`** (COMPARAISON, VOTE) — 2 assets empilés haut/bas (chacun 1080×960, scale+crop),
  ligne de partage, badges "A"/"B", hook centré sur la ligne, CTA bas.
- **`reveal`** (REVELATION) — 1 asset, flou → net progressif (gblur animé) + hook "Attends la
  dernière".

**Invariant rendu :** le texte (overlay ASS) est le **dernier filtre** du graph → toujours
par-dessus les visuels (cohérent avec `montage.render`). Le renderer NE décide RIEN (consomme la
recipe gelée).

---

## 7. Base de données (SQLite, dès V1)

```sql
CREATE TABLE generated_videos (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at    TEXT NOT NULL,
  mechanic_type TEXT NOT NULL,    -- diversité + analytics futur
  content_angle TEXT NOT NULL,    -- angle du hook (A/B testing implicite)
  layout_type   TEXT NOT NULL,
  asset_ids     TEXT NOT NULL,    -- JSON list
  duration      REAL NOT NULL,
  status        TEXT NOT NULL     -- preview | exported | published
);
```
`store.py` expose `insert(recipe, status)` et `query_recent(n)` (la fenêtre glissante lue par le
Policy — T1/T2). Aucun champ de performance en V1.

**Granularité de `history` (figée) :** chaque entrée d'historique lue par le Policy est un triplet
```python
HistoryEntry = {"mechanic": str, "content_angle": str, "layout": str}
```
(= `{mechanic, hook_type, layout_type}`). Ni `mechanic`-only (diversité trop faible), ni
`VideoRecipe` complet (trop bruité). Les 3 dimensions alimentent la fatigue : D1-D3 sur `mechanic`,
D4 sur `content_angle` (orthogonal), et la diversité de `layout` suit `mechanic` en V1 (1 layout par
mécanique). `query_recent(n)` projette exactement ces 3 colonnes de `generated_videos`.

---

## 8. Modules

```
backend/silent/
├── strategy.py    ContentStrategy (intention) + validation
├── policy.py    ★ Policy Engine — decide(strategy, history, registry, seed) → VideoRecipe
├── recipe.py      VideoRecipe (frozen) + validate()
├── registry.py    MECHANICS + LAYOUTS (data-driven)
├── hooks.py       pick_hook(mechanic, rng) → (text, angle)
│   └── hooks/     comparison.json · vote.json · revelation.json
├── render.py      render_recipe(recipe, out) → MP4 1080×1920 (exécution pure)
└── store.py       SQLite generated_videos + query_recent(n)
```

Endpoints serveur (FastAPI) : `/silent/mechanics` (liste registre), `/silent/generate`
(strategy → recipe(s) → render → store → MP4). As-built : `/silent/generate` honore
`count` (batch — l'historique est re-lu entre chaque item, donc la fatigue D0 s'applique à
travers le batch ; `count==1` renvoie `{video_path, recipe}`, `count>1` renvoie `{videos:[…]}`).
Le `/silent/recipe` (build sans render) est **reporté hors V1** (non nécessaire au flux actuel).

UI : toggle de mode "Voix-off / Silencieux" en haut. Panneau silencieux : pick goal/mécanique,
sélection assets (manuel + 🎲 seedé, réutilise la logique inserts photo/vidéo), hook éditable +
re-roll, bouton Générer.

---

## 9. Tests (TDD)

- **strategy** : `goal` → candidats corrects ; `count` respecté ; goal sans mécanique → erreur (P1).
- **policy** : weighted sampling (jamais argmax — S1) ; `repetition_bias` baisse la proba de la
  mécanique récente (D1/D3) ; `pattern_penalty` casse l'ABAB (D2) ; seed reproductible (S3) ;
  recipe immuable (I1) ; layout ∈ allowed (I3) ; durée clampée (I2) ; état invalide → erreur (R1/R2).
- **recipe** : `validate()` rejette mechanic/layout/asset_count/duration invalides (I2, R3).
- **hooks** : tire (text, angle) dans le bon fichier ; re-roll varie ; angle ≠ mécanique (D4).
- **render_recipe** : `split_2` et `reveal` → MP4 1080×1920 de la bonne durée depuis vrais clips.
- **store** : insert + `query_recent(n)` renvoie bien les n dernières dans l'ordre.

---

## 10. Hors périmètre V1 (séquençage strict)

- ❌ Performance score, analytics, learning loop, auto-optimisation (V4/V5)
- ❌ Asset intelligence : tags (V2), prix + marque (V3)
- ❌ Mécaniques TOP3/COLLECTION (V1.1), ELIMINATION/POV (V1.2)
- ❌ Layouts `top3`, `grid_4`, `single` (V1.1/V1.2)
- ❌ Musique de fond (réutilisable depuis le pipeline voix-off plus tard)

## 11. Roadmap

| Version | Contenu |
|---|---|
| **V1** (ce spec) | Policy Engine + 3 mécaniques + hooks + 2 layouts + DB + MP4 |
| V1.1 | TOP3, COLLECTION (+ layouts `top3`, `grid_4`) |
| V1.2 | ELIMINATION, POV (+ layout `single`) |
| V2 | Tags des montres (débloque "montre été/habillée/bleue/...") |
| V3 | Prix + marque (débloque "devine le prix", "moins de 200€") |
| V4 | Récupération stats TikTok / Instagram |
| V5 | Auto-optimisation (performance score → biais de sélection) |
