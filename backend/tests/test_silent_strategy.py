import pytest
from backend.silent.strategy import ContentStrategy, validate_strategy


def test_valid_strategy():
    validate_strategy(ContentStrategy(goal="engagement", count=1))


def test_rejects_unknown_goal():
    with pytest.raises(ValueError, match="goal"):
        validate_strategy(ContentStrategy(goal="virality", count=1))


def test_rejects_count_zero():
    with pytest.raises(ValueError, match="count"):
        validate_strategy(ContentStrategy(goal="engagement", count=0))


def test_rejects_goal_with_no_mechanic():
    with pytest.raises(ValueError, match="goal"):
        validate_strategy(ContentStrategy(goal="nonsense", count=1))


def test_mechanic_override_must_match_goal():
    with pytest.raises(ValueError, match="mechanic"):
        # revelation est 'retention', incompatible avec goal 'engagement'
        validate_strategy(ContentStrategy(goal="engagement", count=1,
                                          mechanic="revelation"))
