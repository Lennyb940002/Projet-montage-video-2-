from collections import Counter
import pytest
from backend.config import SILENT
from backend.silent import policy, registry
from backend.silent.strategy import ContentStrategy
from backend.silent.recipe import VideoRecipe, validate


@pytest.fixture
def neutral_bias(monkeypatch):
    """Neutralise le biais stratégique : teste le MÉCANISME du policy
    (échantillonnage pondéré, biais de répétition) indépendamment de la stratégie produit."""
    monkeypatch.setitem(SILENT, "mechanic_bias", {})


def _decide(strategy, history=None, seed=0):
    return policy.decide(strategy, history or [], seed=seed)


def test_decide_returns_valid_recipe():
    r = _decide(ContentStrategy(goal="engagement", count=1, assets=("a.mp4", "b.mp4")))
    assert isinstance(r, VideoRecipe)
    validate(r)                       # I2/I3/R3
    # engagement + 2 assets -> une mécanique 2-assets de ce goal
    assert r.mechanic in registry.mechanics_for_goal("engagement")
    assert len(r.assets) == 2


def test_decide_is_seed_reproducible():
    s = ContentStrategy(goal="engagement", count=1, assets=("a.mp4", "b.mp4"))
    assert _decide(s, seed=42) == _decide(s, seed=42)          # S3


def test_decide_respects_goal():
    r = _decide(ContentStrategy(goal="retention", count=1, assets=("x.mp4",)))
    assert r.mechanic in registry.mechanics_for_goal("retention")   # P1


def test_decide_honors_mechanic_override():
    r = _decide(ContentStrategy(goal="engagement", count=1,
                                mechanic="vote", assets=("a.mp4", "b.mp4")))
    assert r.mechanic == "vote"


def test_repetition_bias_reduces_recent_mechanic(neutral_bias):
    # Invariant D1/D3 : une mécanique récemment répétée est sous-pondérée (soft,
    # jamais exclue). Test robuste au roster : 'comparison' est tirée MOINS avec un
    # historique saturé de 'comparison' que sans historique.
    def picks(history, n=100):
        c = Counter()
        for seed in range(n):
            r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                              assets=("a.mp4", "b.mp4")),
                              history, seed=seed)
            c[r.mechanic] += 1
        return c
    hist = [{"mechanic": "comparison", "content_angle": "a_or_b",
             "layout": "split_2"}] * 5
    penalized = picks(hist)
    baseline = picks([])
    assert penalized["comparison"] < baseline["comparison"]     # D1/D3 (biais, pas interdit)
    assert penalized["comparison"] > 0                          # jamais exclusion dure


def test_decide_uses_weighted_not_argmax(neutral_bias):
    # Sans historique, sur 60 seeds, les 2 mécaniques engagement apparaissent.
    counts = Counter()
    for seed in range(60):
        r = policy.decide(ContentStrategy(goal="engagement", count=1,
                                          assets=("a.mp4", "b.mp4")),
                          [], seed=seed)
        counts[r.mechanic] += 1
    assert counts["comparison"] > 0 and counts["vote"] > 0      # S1 (pas argmax)


def test_banned_mechanics_never_proposed():
    """Aucune mécanique bannie ne doit sortir de decide() sur 200 seeds (Phase 0)."""
    banned = {"comparison", "vote", "elimination", "top3", "battle",
              "transformation", "erreur", "pov", "collection",
              "comparison_4", "collection_4", "revelation"}
    seen = set()
    for s in range(200):
        r = policy.decide(ContentStrategy(goal="engagement", count=1), history=[], seed=s)
        seen.add(r.mechanic)
    assert not (seen & banned), f"mécanique bannie sortie : {seen & banned}"
