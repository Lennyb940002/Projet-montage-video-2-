import pytest
pytestmark = pytest.mark.skip(reason="V2 en pause — rollback V1 demande proprietaire 2026-07-03")
import random
import backend.silent.hooks as h
from backend.silent import canon


def test_hook_generator_never_returns_banned(monkeypatch):
    pool = [("Choisis ta montre, elle révèle qui tu es", "identite"),
            ("La Seiko Daytona qu'il te faut", "banned"),
            ("Cette pièce cache un secret", "reveal")]
    monkeypatch.setattr(h._concepts, "hooks_for", lambda m: pool)
    for seed in range(60):
        text, angle = h.pick_hook("test", random.Random(seed))
        assert canon.is_clean(text)
        assert angle != "banned"


def test_hook_generator_sanitizes_when_whole_bank_dirty(monkeypatch):
    monkeypatch.setattr(h._concepts, "hooks_for",
                        lambda m: [("Une Seiko Daytona Or rose", "a"), ("La Datejust", "b")])
    text, _ = h.pick_hook("test", random.Random(0))
    assert canon.is_clean(text)
