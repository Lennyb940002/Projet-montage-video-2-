import os
from backend.silent.render import render_recipe
from backend.silent.recipe import VideoRecipe
from backend import ffmpeg

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
IMG = os.path.join(FIX, "sample_insert.png")
VID = os.path.join(FIX, "sample_insert.mp4")


def test_render_split_2_produces_vertical_mp4(tmp_path):
    r = VideoRecipe(mechanic="comparison", layout="split_2",
                    hook="A ou B ?", content_angle="a_or_b",
                    assets=(IMG, VID), duration=5.0,
                    font="Arial Black", accent="&H0000FFFF&",
                    text_anim="pop", seed=1)
    out = str(tmp_path / "cmp.mp4")
    render_recipe(r, out)
    assert os.path.exists(out)
    probe = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", out])
    assert "1080,1920" in probe.stdout
    assert abs(ffmpeg.probe_duration(out) - 5.0) < 0.5


def test_end_to_end_comparison_strategy_to_mp4(tmp_path, monkeypatch):
    """ContentStrategy -> Policy -> Recipe -> Renderer -> Store, sur vrais assets."""
    import random
    from backend.silent.strategy import ContentStrategy, validate_strategy
    from backend.silent import policy
    from backend.silent.store import Store

    strat = ContentStrategy(goal="engagement", count=1, mechanic="comparison",
                            assets=(IMG, VID))
    validate_strategy(strat)
    recipe = policy.decide(strat, history=[], seed=7)
    assert recipe.mechanic == "comparison" and recipe.layout == "split_2"

    out = str(tmp_path / "e2e.mp4")
    render_recipe(recipe, out)
    assert os.path.exists(out)

    store = Store(str(tmp_path / "e2e.db"))
    store.insert(recipe, status="preview")
    recent = store.query_recent(1)
    assert recent[0]["mechanic"] == "comparison"
    assert recent[0]["content_angle"] == recipe.content_angle
