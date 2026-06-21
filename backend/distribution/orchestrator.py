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
from backend import settings
from backend.distribution import uploadpost


# Cycle d'anti-répétition : une montre/musique ne réapparaît pas avant N vidéos.
CYCLE = 2   # "jamais les mêmes montres dans 3 vidéos consécutives"


def _decide_recipe(goal, seed, exclude_models=(), exclude_music=()):
    strat = ContentStrategy(goal=goal, count=1)
    return _policy.decide(strat, history=[], seed=seed,
                          exclude_models=exclude_models, exclude_music=exclude_music)


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
    # Anti-répétition : éviter montres + musiques des CYCLE dernières vidéos.
    recipe = _decide_recipe(goal, seed,
                            exclude_models=store.recent_models(CYCLE),
                            exclude_music=store.recent_music(CYCLE))
    out = os.path.join(out_dir, "dist_" + uuid.uuid4().hex + ".mp4")
    _render(recipe, out)
    caption, tags = caption_seo.build_caption(
        mechanic=recipe.mechanic, model_names=_model_names(recipe), hook=recipe.hook)
    full = caption + ("\n\n" + " ".join(tags) if tags else "")
    pid = store.insert(video_path=out, mechanic=recipe.mechanic,
                       content_angle=recipe.content_angle, layout=recipe.layout,
                       asset_ids=list(recipe.assets), caption=full, music=recipe.music)
    return {"pid": pid, "video_path": out, "caption": full}


# Décision -> statut final. 'approve'/'timeout' postent ; 'skip' non.
_POST_STATUS = {"approve": "posted", "timeout": "auto_posted"}


def _do_post(row):
    s = settings.load()
    return uploadpost.post(row["video_path"], row["caption"], ["tiktok", "instagram"],
                           user=s.get("uploadpost_user", ""),
                           token=s.get("uploadpost_token", ""))


def decide_and_post(pid, decision, store=None):
    """Applique la décision (approve|skip|timeout) : poste si besoin, met le
    statut. NON BLOQUANT : échec post -> statut 'failed'."""
    store = store or DistStore(SILENT_DB)
    row = store.get(pid)
    if not row or row["status"] != "pending":
        return
    if decision == "skip":
        store.update_status(pid, "skipped")
        return
    res = _do_post(row)
    if res.get("ok"):
        store.update_status(pid, _POST_STATUS.get(decision, "posted"))
    else:
        store.update_status(pid, "failed")
