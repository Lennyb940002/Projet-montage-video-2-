import pytest

from backend.silent.recipe import VideoRecipe
from backend.silent import render


def _recipe(mechanic, labels):
    return VideoRecipe(mechanic=mechanic, layout="split_3", hook="H", content_angle="a",
                       assets=("x", "y", "z"), duration=6.0, font="Impact",
                       accent="&H0000FFFF&", text_anim="fade", seed=1, labels=labels)


def test_cell_labels_uses_recipe_labels():
    L = (("discret", "&H0000FFFF&"), ("froid", "&H0000FF00&"), ("carré", "&H009314FF&"))
    assert render._cell_labels(_recipe("test", L)) == list(L)


def test_1a_without_labels_fails_hard():
    for m in ["test", "revelation_psy", "trahison", "perception", "test_perso"]:
        with pytest.raises(ValueError):
            render._cell_labels(_recipe(m, None))
