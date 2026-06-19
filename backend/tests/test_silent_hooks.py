import random
from backend.silent import hooks


def test_pick_hook_returns_text_and_angle():
    text, angle = hooks.pick_hook("comparison", random.Random(1))
    assert isinstance(text, str) and text
    assert isinstance(angle, str) and angle


def test_pick_hook_angle_in_file():
    entries = hooks.load_hooks("comparison")
    angles = {e["angle"] for e in entries}
    _, angle = hooks.pick_hook("comparison", random.Random(7))
    assert angle in angles


def test_pick_hook_reroll_varies():
    got = {hooks.pick_hook("comparison", random.Random(s))[0] for s in range(20)}
    assert len(got) > 1


def test_all_v1_mechanics_have_hook_files():
    for mech in ("comparison", "vote", "revelation"):
        assert hooks.load_hooks(mech), f"no hooks for {mech}"
