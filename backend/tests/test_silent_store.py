from backend.silent.store import Store
from backend.silent.recipe import VideoRecipe


def _recipe(mech, angle, layout, assets):
    return VideoRecipe(mechanic=mech, layout=layout, hook="h",
                       content_angle=angle, assets=assets, duration=6.0,
                       font="Arial Black", accent="&H0000FFFF&",
                       text_anim="pop", seed=1)


def test_insert_and_query_recent_order(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    s.insert(_recipe("comparison", "a_or_b", "split_2", ("a", "b")), status="preview")
    s.insert(_recipe("vote", "vote_cta", "split_2", ("c", "d")), status="preview")
    s.insert(_recipe("revelation", "wait_last", "reveal", ("e",)), status="exported")
    recent = s.query_recent(2)
    # Plus récent d'abord
    assert [e["mechanic"] for e in recent] == ["revelation", "vote"]
    # Granularité figée : 3 dimensions exactement
    assert set(recent[0]) == {"mechanic", "content_angle", "layout"}


def test_query_recent_empty_db_returns_empty(tmp_path):
    s = Store(str(tmp_path / "empty.db"))
    assert s.query_recent(5) == []
