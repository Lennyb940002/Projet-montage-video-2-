import random
from collections import Counter
import pytest
from backend.silent import policy
from backend.silent.strategy import ContentStrategy
from backend.silent.recipe import VideoRecipe, validate


def _decide(strategy, history=None, seed=0):
    return policy.decide(strategy, history or [], seed=seed)


def test_decide_returns_valid_recipe():
    r = _decide(ContentStrategy(goal="engagement", count=1, assets=("a.mp4", "b.mp4")))
    assert isinstance(r, VideoRecipe)
    validate(r)                       # I2/I3/R3
    assert r.mechanic in ("comparison", "vote")


def test_decide_is_seed_reproducible():
    s = ContentStrategy(goal="engagement", count=1, assets=("a.mp4", "b.mp4"))
    assert _decide(s, seed=42) == _decide(s, seed=42)          # S3


def test_decide_respects_goal():
    r = _decide(ContentStrategy(goal="retention", count=1, assets=("x.mp4",)))
    assert r.mechanic == "revelation"                           # P1


def test_decide_honors_mechanic_override():
    r = _decide(ContentStrategy(goal="engagement", count=1,
                                mechanic="vote", assets=("a.mp4", "b.mp4")))
    assert r.mechanic == "vote"


def test_repetition_bias_reduces_recent_mechanic():
    # Historique saturé de 'comparison' -> sur de nombreux seeds, 'vote' domine.
    history = [{"mechanic": "comparison", "content_angle": "a_or_b",
                "layout": "split_2"}] * 5
    counts = Counter()
    for seed in range(60):
        r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                          assets=("a.mp4", "b.mp4")),
                          history, seed=seed)
        counts[r.mechanic] += 1
    assert counts["vote"] > counts["comparison"]                # D1/D3 (biais, pas interdit)
    assert counts["comparison"] > 0                             # jamais exclusion dure


def test_decide_uses_weighted_not_argmax():
    # Sans historique, sur 60 seeds, les 2 mécaniques engagement apparaissent.
    counts = Counter()
    for seed in range(60):
        r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                          assets=("a.mp4", "b.mp4")),
                          [], seed=seed)
        counts[r.mechanic] += 1
    assert counts["comparison"] > 0 and counts["vote"] > 0      # S1 (pas argmax)
