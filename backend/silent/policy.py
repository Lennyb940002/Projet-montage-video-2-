"""Policy Engine — SEUL système de décision. Fonction pure :
    decide(strategy, history, seed) -> VideoRecipe (immuable)

Double rôle : constraint solver + stochastic sampler ET sequence stabilizer (D0).
Fatigue = soft scoring (S1/S2), jamais exclusion dure. Aucun effet de bord, aucune
métrique externe (V1). Les assets imposés viennent de `strategy.assets` (Option C :
contrainte forte) ; sinon le Sampler tire depuis la banque."""
import math
import random as _random
from backend.config import SILENT
from backend.silent import registry, hooks, sampler, content
from backend.silent import music as _music
from backend.silent.recipe import VideoRecipe, validate


def _occurrences(mechanic, window):
    return sum(1 for h in window if h["mechanic"] == mechanic)


def _is_short_cycle(mechanic, window):
    """1 si choisir `mechanic` prolongerait une alternance ABAB.
    window = historique récent (plus récent d'abord)."""
    if len(window) >= 2 and window[1]["mechanic"] == mechanic \
            and window[0]["mechanic"] != mechanic:
        return 1
    return 0


def _weighted_choice(scored, temperature, rng):
    """Softmax sur les scores -> tirage pondéré (S1/S2). `scored` = [(item, score)]."""
    items = [it for it, _ in scored]
    exps = [math.exp(s / temperature) for _, s in scored]
    total = sum(exps)
    weights = [e / total for e in exps]
    r = rng.random()
    cum = 0.0
    for it, w in zip(items, weights):
        cum += w
        if r <= cum:
            return it
    # Filet de sécurité fp : si la somme des poids retombe à 0.9999… par erreur
    # d'arrondi et que r tombe dans ce micro-écart, on renvoie le dernier item.
    # Cas extrêmement rare ; ce n'est PAS du code mort.
    return items[-1]


def decide(strategy, history, seed, exclude_models=(), exclude_music=()):
    """Traduit une intention en VideoRecipe validé. Lève ValueError si état
    invalide (R1 : pas de fallback silencieux).

    `exclude_models` / `exclude_music` : montres et sons des vidéos récentes,
    évités en priorité par le sampler et le bed musical (anti-répétition)."""
    rng = _random.Random(seed)

    candidates = registry.mechanics_for_goal(strategy.goal)
    if not candidates:
        raise ValueError(f"no mechanic for goal {strategy.goal!r}")            # P1
    if strategy.mechanic is not None:
        if strategy.mechanic not in candidates:
            raise ValueError(f"mechanic {strategy.mechanic!r} not in {candidates}")
        candidates = [strategy.mechanic]                                       # I4 read-only

    # Si des assets sont imposés, ne garder que les mécaniques dont l'asset_count
    # correspond (sinon on choisirait une méca incompatible -> échec validate).
    if strategy.assets is not None:
        n = len(strategy.assets)
        sized = [m for m in candidates
                 if registry.MECHANICS[m]["asset_count"] == n]
        if not sized:
            raise ValueError(
                f"no mechanic for goal {strategy.goal!r} accepts {n} assets")
        candidates = sized

    # Biais stratégique par mécanique (favorise/réduit/bannit). Les bannies
    # (biais 0) sont retirées de la rotation — sauf si la mécanique est imposée
    # explicitement (I4 : override utilisateur respecté).
    bias = SILENT.get("mechanic_bias", {})
    if strategy.mechanic is None:
        kept = [m for m in candidates if bias.get(m, 1.0) > 0]
        if kept:
            candidates = kept

    window = list(history)[:SILENT["window_n"]]   # plus récent d'abord (cf store)
    denom = max(1, len(window))
    temp = SILENT["temperature"]
    scored = []
    for m in candidates:
        score = (SILENT["base_score"]
                 - SILENT["w_rep"] * _occurrences(m, window) / denom            # D1/D3
                 - SILENT["w_pat"] * _is_short_cycle(m, window))                # D2
        b = bias.get(m, 1.0)
        if b > 0:
            score += temp * math.log(b)   # biais multiplicatif exact sur le poids softmax
        scored.append((m, score))
    mechanic = _weighted_choice(scored, SILENT["temperature"], rng)            # S1/S2/S3

    meta = registry.MECHANICS[mechanic]
    layout = rng.choice(meta["layouts"])                                       # I3
    hook, angle = hooks.pick_hook(mechanic, rng)                               # D4 orthogonal

    # Assets — Option C : Policy émet la contrainte, Sampler réalise le tirage.
    # strategy.assets (pick manuel UI) = contrainte forte ; sinon tirage en banque.
    constraint = {"count": meta["asset_count"], "filters": {}}
    if strategy.assets is not None:
        assets = tuple(strategy.assets)
        if len(assets) != meta["asset_count"]:
            raise ValueError(
                f"strategy.assets count {len(assets)} != {meta['asset_count']}")
    else:
        assets = tuple(sampler.sample(constraint, rng, exclude_models=exclude_models))

    duration = max(SILENT["min_duration"],
                   min(SILENT["max_duration"], meta["default_duration"]))

    # Formats 1A : labels (profils/phrases) + CTA décidés ici (jamais dans le renderer).
    _FORMATS_1A = {"test", "revelation_psy", "trahison", "perception", "test_perso"}
    labels = cta_type = None
    if mechanic in _FORMATS_1A:
        labels, _ = content.pick_labels(mechanic, assets, rng)
        _, cta_type = content.pick_cta(mechanic, rng)

    recipe = VideoRecipe(
        mechanic=mechanic, layout=layout, hook=hook, content_angle=angle,
        assets=assets, duration=duration,
        font=rng.choice(SILENT["fonts"]), accent=rng.choice(SILENT["accents"]),
        text_anim=rng.choice(SILENT["text_anims"]), seed=seed,
        music=_music.pick_track(rng, exclude=exclude_music),   # son seedé, anti-répétition
        labels=labels, cta_type=cta_type)
    return validate(recipe)                                                    # R3
