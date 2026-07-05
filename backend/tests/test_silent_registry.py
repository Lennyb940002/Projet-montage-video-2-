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
        "test", "projection", "battle", "transformation", "erreur", "pov",
        "comparison_4", "collection_4",
        # formats 1A (guide 2026-07-05)
        "revelation_psy", "trahison", "perception", "test_perso"}


def test_formats_1a_present():
    for m in ["test", "revelation_psy", "trahison", "perception", "test_perso"]:
        meta = registry.MECHANICS[m]
        assert meta["asset_count"] == 3
        assert meta["layouts"] == ["split_3"]
        assert meta["goal"] == "engagement"
    assert registry.MECHANICS["revelation_psy"]["label_mode"] == "psycho"
    assert registry.MECHANICS["trahison"]["label_mode"] == "trahison"
    assert registry.MECHANICS["perception"]["label_mode"] == "perception"
    assert registry.MECHANICS["test_perso"]["label_mode"] == "test_reveal"


def test_mechanics_for_goal_filters():
    eng = set(registry.mechanics_for_goal("engagement"))
    assert {"comparison", "vote", "collection", "elimination", "top3",
            "battle"} <= eng
    assert set(registry.mechanics_for_goal("retention")) == {"revelation", "pov"}
    assert registry.mechanics_for_goal("nope") == []
