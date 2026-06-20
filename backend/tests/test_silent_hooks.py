import random
from backend.silent import hooks


def test_pick_hook_returns_text_and_angle():
    text, angle = hooks.pick_hook("comparison", random.Random(1))
    assert isinstance(text, str) and text
    assert isinstance(angle, str) and angle


def test_pick_hook_text_in_active_pool():
    # Pool actif = dossier concepts si dispo, sinon JSON intégré.
    from backend.silent import concepts
    dossier = [t for t, _ in concepts.hooks_for("comparison")]
    jsonp = [e["text"] for e in hooks.load_hooks("comparison")]
    pool = set(dossier) | set(jsonp)
    text, angle = hooks.pick_hook("comparison", random.Random(7))
    assert text in pool and angle


def test_pick_hook_reroll_varies():
    got = {hooks.pick_hook("comparison", random.Random(s))[0] for s in range(20)}
    assert len(got) > 1


def test_all_v1_mechanics_have_hook_files():
    for mech in ("comparison", "vote", "revelation"):
        assert hooks.load_hooks(mech), f"no hooks for {mech}"
