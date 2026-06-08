# Pack Dynamisme — Design

**Date :** 2026-06-08
**Statut :** Design validé
**Contexte :** Premier sous-projet de la vision « moteur de montage auto ». Rend les vidéos nettement plus « montées par un humain » sans nouvel asset : emphase des sous-titres, motion animé, transitions. Architecture pensée extensible (Director / sémantique / B-roll plus tard).

## Ordre validé
1. Emphase sous-titres → 2. Motion engine → 3. Transitions. (Musique = sous-projet suivant.)

## Clé de voûte (extensibilité)
- **`backend/pipeline/keywords.py`** : source unique des « mots à forte valeur » (marques, chiffres, prix, CTA, superlatifs : incroyable, jamais, fou, énorme, dingue, ouf, record…). API : `mark(tokens)` → annote `t["kw"]=True`. Réutilisé par emphase + punch motion + (futur) overlays.
- **`backend/pipeline/director.py`** : embryon du moteur de règles. `build_plan(tokens, n_sent, ranges, duration)` → 
  ```
  {"motion": [{"kind","start","end","params"}],
   "transitions": [{"at","type"}]}
  ```
  (Les sous-titres consomment directement `tokens` annotés ; les SFX restent gérés par `sfx_plan`.) Aujourd'hui = règles simples ; demain enrichi sans refactor. `montage.render` consomme `motion` + `transitions`.

## Brick 1 — Emphase sous-titres (`subtitles.py`)
- Nouveau style **`premium_pop`** (mode `"premium"`), les styles existants intacts.
- Rendu **mot par mot** : pour chaque mot, un évènement `Dialogue` `[mot.start, mot_suivant.start)` montrant le bloc (≤3 mots) ; le mot **actif** = `scale 130→100` (`\t`, pop) + couleur accent ; mots normaux = blanc. **Mot-clé actif** = plus gros (taille ×1.25) + glow (outline accent) + **bounce** (overshoot `\t` 145→95→100).
- **Sans `\fad`** (anti-clignotement) ; lignes contiguës.
- Config **`EMPHASIS`** : `kw_scale`, `active_scale`, `accent_color`, `kw_size_mult`.

## Brick 2 — Motion engine (`montage.py`) — risque n°1
- **Ken Burns** léger par clip + **punch** sur mots-clés + **shake** sur révélations/chiffres.
- **Spike obligatoire avant code** : valider une méthode de **zoom animé qui préserve le mouvement** (test : 2 frames du même clip diffèrent). `zoompan` fige ; `crop:eval=frame` indisponible. Repli si échec : **zoom constant varié par clip** + punch par ré-échelonnage bref.
- **Shake** = `crop` avec `x/y` oscillants (`sin`) sur fenêtre `enable='between(t,T,T+0.3)'` (position animée = supporté).
- Config **`MOTION`** : `kenburns_rate`, `punch_scale`, `shake_px`, `zoom_period` (2–3 s).

## Brick 3 — Transitions (`montage.py`)
- À chaque cut : **fade/blur rapide ~0,12 s en début de clip** → **préserve la durée totale** (sync voix intacte).
- Type choisi selon contexte (phrase = fade ; mot fort/hook = zoom-punch ; énergie = whip léger).
- **Limite** : transitions à recouvrement (`xfade`, whip réel) raccourcissent la timeline → reportées (nécessitent recalcul de timeline). v1 = length-preserving.
- Config **`TRANSITIONS`** : `dur`, `default_type`.

## Intégration
- `service.make_video` : construit `tokens` (déjà), `keywords.mark(tokens)`, `plan = director.build_plan(...)`, passe `tokens` au builder premium si style premium, et `plan` à `montage.render`.
- `montage.render(..., plan=None)` : si `plan`, applique motion (zoom/punch/shake) par clip + transitions au montage vidéo. Rétro-compatible (`plan=None` = comportement actuel).
- Frontend : style `premium_pop` apparaît auto dans le menu. Motion/transitions = actifs via config (et liés au rendu standard ; pas de nouveau bouton requis).

## Erreurs & tests
- `keywords.mark` : marque marques/chiffres/prix/CTA/superlatifs, pas les mots neutres.
- `subtitles` premium : produit du `\t` (anim), couleur accent, taille majorée sur kw, pas de `\k` ni `\fad`.
- `director.build_plan` : renvoie motion (zoom périodique + punch aux mots-clés) + transitions aux cuts.
- `montage.render(plan=...)` : vidéo 1080×1920 valide ; **spike motion** vérifie le mouvement préservé.
- Non-régression : styles existants + rendu sans `plan` inchangés.

## Hors périmètre (plus tard)
Musique de fond, overlays graphiques, transitions à recouvrement (whip réel), analyse sémantique, B-roll par contenu, Director complet.
