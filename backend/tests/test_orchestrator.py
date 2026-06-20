import backend.distribution.orchestrator as orch


def test_generate_for_slot_builds_recipe_caption_and_inserts(tmp_path, monkeypatch):
    from backend.silent.recipe import VideoRecipe
    fake_recipe = VideoRecipe(mechanic="comparison", layout="split_2", hook="A ou B ?",
                              content_angle="a_or_b", assets=("C:/Rainbow Or rose/x.mp4",),
                              duration=5.0, font="Arial Black", accent="&H00FFFFFF&",
                              text_anim="pop", seed=1)
    monkeypatch.setattr(orch, "_decide_recipe", lambda goal, seed: fake_recipe)
    monkeypatch.setattr(orch, "_render", lambda recipe, out: out)
    monkeypatch.setattr(orch.caption_seo, "build_caption",
                        lambda **k: ("ma caption", ["#montre"]))
    store = orch.DistStore(str(tmp_path / "d.db"))
    res = orch.generate_for_slot(goal="engagement", seed=1, store=store,
                                 out_dir=str(tmp_path))
    assert res["pid"] > 0
    row = store.get(res["pid"])
    assert row["status"] == "pending" and row["caption"] == "ma caption\n\n#montre"
    assert res["video_path"].endswith(".mp4")
