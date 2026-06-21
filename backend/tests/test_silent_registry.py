from backend.silent import registry


def test_mechanics_have_required_fields():
    for name, m in registry.MECHANICS.items():
        assert m["goal"] in ("engagement", "retention")
        assert isinstance(m["asset_count"], int) and m["asset_count"] >= 1
        assert m["layouts"] and all(l in registry.LAYOUTS for l in m["layouts"])
        assert m["hook_file"].endswith(".json")
        assert m["default_duration"] > 0


def test_mechanics_set():
    assert set(registry.MECHANICS) == {
        "comparison", "vote", "revelation", "collection", "elimination", "top3",
        "test", "battle", "transformation", "erreur", "pov",
        "comparison_4", "collection_4"}


def test_mechanics_for_goal_filters():
    eng = set(registry.mechanics_for_goal("engagement"))
    assert {"comparison", "vote", "collection", "elimination", "top3",
            "battle"} <= eng
    assert set(registry.mechanics_for_goal("retention")) == {"revelation", "pov"}
    assert registry.mechanics_for_goal("nope") == []
