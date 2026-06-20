"""Orchestration d'un créneau : décide une recipe -> rend -> caption -> insère
en DB (statut pending). Le post effectif est déclenché par le bot Telegram
(approbation) ou le timeout. NON BLOQUANT."""
import os, uuid
from backend.config import WORKDIR, SILENT, SILENT_DB
from backend.silent import policy as _policy
from backend.silent.strategy import ContentStrategy
from backend.silent.render import render_recipe
from backend.distribution import caption_seo
from backend.distribution.store import DistStore


def _decide_recipe(goal, seed):
    strat = ContentStrategy(goal=goal, count=1)
    return _policy.decide(strat, history=[], seed=seed)


def _render(recipe, out_path):
    return render_recipe(recipe, out_path)


def _model_names(recipe):
    models = SILENT.get("models") or {}
    out = []
    for a in recipe.assets:
        folder = os.path.basename(os.path.dirname(a))
        out.append((models.get(folder) or {}).get("name", folder))
    return out


def generate_for_slot(goal, seed, store=None, out_dir=None):
    """Produit une vidéo + caption pour un créneau, l'insère 'pending'.
    Renvoie {pid, video_path, caption}."""
    store = store or DistStore(SILENT_DB)
    out_dir = out_dir or WORKDIR
    recipe = _decide_recipe(goal, seed)
    out = os.path.join(out_dir, "dist_" + uuid.uuid4().hex + ".mp4")
    _render(recipe, out)
    caption, tags = caption_seo.build_caption(
        mechanic=recipe.mechanic, model_names=_model_names(recipe), hook=recipe.hook)
    full = caption + ("\n\n" + " ".join(tags) if tags else "")
    pid = store.insert(video_path=out, mechanic=recipe.mechanic,
                       content_angle=recipe.content_angle, layout=recipe.layout,
                       asset_ids=list(recipe.assets), caption=full)
    return {"pid": pid, "video_path": out, "caption": full}
