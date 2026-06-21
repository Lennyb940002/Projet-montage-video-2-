"""Filet de sécurité architectural — invariants transverses du Policy Engine.
Vérifie sur TOUTES les mécaniques que les contrats tiennent ensemble."""
import dataclasses
from collections import Counter
import pytest
from backend.silent import registry, hooks, policy
from backend.silent.strategy import ContentStrategy
from backend.silent.recipe import VideoRecipe, validate

_FAKE = {1: ("a.mp4",), 2: ("a.mp4", "b.mp4"),
         3: ("a.mp4", "b.mp4", "c.mp4"),
         4: ("a.mp4", "b.mp4", "c.mp4", "d.mp4")}  # assets bidon par asset_count


def _strategy_for(mechanic):
    goal = registry.MECHANICS[mechanic]["goal"]
    n = registry.MECHANICS[mechanic]["asset_count"]
    return ContentStrategy(goal=goal, count=1, mechanic=mechanic, assets=_FAKE[n])


def test_I1_every_produced_recipe_is_immutable():
    for mech in registry.MECHANICS:
        r = policy.decide(_strategy_for(mech), [], seed=1)
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.mechanic = "x"


def test_I2_I3_every_produced_recipe_validates():
    for mech in registry.MECHANICS:
        for seed in range(10):
            r = policy.decide(_strategy_for(mech), [], seed=seed)
            validate(r)                                  # I2 + I3 + duration range


def test_layout_always_in_allowed_set():
    for mech in registry.MECHANICS:
        allowed = registry.MECHANICS[mech]["layouts"]
        for seed in range(10):
            r = policy.decide(_strategy_for(mech), [], seed=seed)
            assert r.layout in allowed                    # I3


def test_hooks_valid_for_all_mechanics():
    for mech in registry.MECHANICS:
        entries = hooks.load_hooks(mech)
        assert entries and all("text" in e and "angle" in e for e in entries)


def test_P1_every_goal_maps_to_mechanic():
    for goal in ("engagement", "retention"):
        assert registry.mechanics_for_goal(goal)


def test_S1_selection_is_weighted_not_argmax():
    # Sans contrainte de mécanique, les 2 mécaniques engagement apparaissent.
    counts = Counter()
    for seed in range(80):
        r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                          assets=("a.mp4", "b.mp4")), [], seed=seed)
        counts[r.mechanic] += 1
    assert counts["comparison"] > 0 and counts["vote"] > 0


def test_S3_seed_determinism_across_mechanics():
    for mech in registry.MECHANICS:
        s = _strategy_for(mech)
        assert policy.decide(s, [], seed=99) == policy.decide(s, [], seed=99)


def test_D1_D3_no_hard_exclusion_but_biased():
    # Historique saturé d'une mécanique : elle reste possible (pas d'exclusion dure)
    # mais minoritaire (biais).
    hist = [{"mechanic": "comparison", "content_angle": "a_or_b",
             "layout": "split_2"}] * 5
    counts = Counter()
    for seed in range(80):
        r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                          assets=("a.mp4", "b.mp4")), hist, seed=seed)
        counts[r.mechanic] += 1
    assert counts["comparison"] > 0                       # jamais 0 (soft)
    assert counts["vote"] > counts["comparison"]          # biais vers diversité
