"""Orchestration HTTP du Silent Engine : strategy -> policy -> render -> store."""
import os, uuid, dataclasses
from backend.config import WORKDIR, SILENT_DB, SILENT
from backend.silent import registry, policy
from backend.silent.strategy import ContentStrategy, validate_strategy
from backend.silent.render import render_recipe
from backend.silent.store import Store

_store = Store(SILENT_DB)


def list_mechanics():
    return [{"name": n, "goal": m["goal"], "asset_count": m["asset_count"]}
            for n, m in registry.MECHANICS.items()]


def generate(goal, mechanic=None, assets=None, seed=0, out_path=None, count=1):
    """Génère `count` vidéos (P3 : count recipes produits).

    L'historique est RE-LU entre chaque itération : la fatigue/diversité du
    Policy s'applique donc à travers le batch (sequence stabilizer D0). Le seed
    est avancé par item pour la variété. count==1 conserve la forme
    {video_path, recipe} (compat UI) ; count>1 renvoie {videos: [...]}."""
    strat = ContentStrategy(goal=goal, count=count, mechanic=mechanic,
                            assets=tuple(assets) if assets else None)
    validate_strategy(strat)
    results = []
    for i in range(count):
        history = _store.query_recent(SILENT["window_n"])
        recipe = policy.decide(strat, history, seed=seed + i)
        # out_path explicite seulement en génération unique ; en batch chaque
        # vidéo reçoit un chemin distinct.
        out = (out_path if (count == 1 and out_path)
               else os.path.join(WORKDIR, "silent_" + uuid.uuid4().hex + ".mp4"))
        render_recipe(recipe, out)
        _store.insert(recipe, status="preview")
        results.append({"video_path": out, "recipe": dataclasses.asdict(recipe)})
    return results[0] if count == 1 else {"videos": results}
