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


def generate(goal, mechanic=None, assets=None, seed=0, out_path=None):
    strat = ContentStrategy(goal=goal, count=1, mechanic=mechanic,
                            assets=tuple(assets) if assets else None)
    validate_strategy(strat)
    history = _store.query_recent(SILENT["window_n"])
    recipe = policy.decide(strat, history, seed=seed)
    out = out_path or os.path.join(WORKDIR, "silent_" + uuid.uuid4().hex + ".mp4")
    render_recipe(recipe, out)
    _store.insert(recipe, status="preview")
    return {"video_path": out, "recipe": dataclasses.asdict(recipe)}
