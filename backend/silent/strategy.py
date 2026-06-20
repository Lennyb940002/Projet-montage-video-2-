"""ContentStrategy : couche INTENTION. Le Policy la lit sans jamais la muter (I4)."""
from dataclasses import dataclass
from backend.silent import registry

_GOALS = ("engagement", "retention")


@dataclass(frozen=True)
class ContentStrategy:
    goal: str
    count: int
    mechanic: str = None       # override optionnel
    assets: tuple = None       # assets imposés (pick manuel UI)


def validate_strategy(strategy):
    """Valide l'intention avant décision (P1, P3, R2)."""
    if strategy.goal not in _GOALS:
        raise ValueError(f"unknown goal: {strategy.goal!r} (expected {_GOALS})")
    if strategy.count < 1:
        raise ValueError(f"count must be >= 1, got {strategy.count}")
    candidates = registry.mechanics_for_goal(strategy.goal)
    if not candidates:
        raise ValueError(f"no mechanic maps to goal {strategy.goal!r}")        # P1
    if strategy.mechanic is not None and strategy.mechanic not in candidates:
        raise ValueError(
            f"mechanic {strategy.mechanic!r} not valid for goal "
            f"{strategy.goal!r} (candidates: {candidates})")                    # I4/P2
    return strategy
