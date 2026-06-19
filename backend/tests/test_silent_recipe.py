import dataclasses
import pytest
from backend.silent.recipe import VideoRecipe, validate


def _ok_recipe(**over):
    base = dict(mechanic="comparison", layout="split_2",
                hook="A ou B ?", content_angle="a_or_b",
                assets=("a.mp4", "b.mp4"), duration=6.0,
                font="Arial Black", accent="&H0000FFFF&",
                text_anim="pop", seed=42)
    base.update(over)
    return VideoRecipe(**base)


def test_recipe_is_immutable():
    r = _ok_recipe()
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.mechanic = "vote"


def test_validate_accepts_valid_recipe():
    validate(_ok_recipe())  # no raise


def test_validate_rejects_unknown_mechanic():
    with pytest.raises(ValueError, match="mechanic"):
        validate(_ok_recipe(mechanic="ghost"))


def test_validate_rejects_layout_not_allowed_for_mechanic():
    with pytest.raises(ValueError, match="layout"):
        validate(_ok_recipe(layout="reveal"))  # reveal not allowed for comparison


def test_validate_rejects_wrong_asset_count():
    with pytest.raises(ValueError, match="asset"):
        validate(_ok_recipe(assets=("only_one.mp4",)))


def test_validate_rejects_duration_out_of_range():
    with pytest.raises(ValueError, match="duration"):
        validate(_ok_recipe(duration=99.0))
