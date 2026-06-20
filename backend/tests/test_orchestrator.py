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


def test_decide_and_post_approved(tmp_path, monkeypatch):
    store = orch.DistStore(str(tmp_path / "d.db"))
    pid = store.insert(video_path="v.mp4", mechanic="comparison", content_angle="a",
                       layout="split_2", asset_ids=["x"], caption="cap")
    posted = {}

    def _fake_post(row):
        posted["v"] = row["video_path"]
        return {"ok": True}

    monkeypatch.setattr(orch, "_do_post", _fake_post)
    orch.decide_and_post(pid, "approve", store=store)
    assert store.get(pid)["status"] == "posted" and posted["v"] == "v.mp4"


def test_decide_and_post_skip(tmp_path, monkeypatch):
    store = orch.DistStore(str(tmp_path / "d.db"))
    pid = store.insert(video_path="v", mechanic="vote", content_angle="a",
                       layout="split_2", asset_ids=["x"], caption="c")
    monkeypatch.setattr(orch, "_do_post", lambda row: (_ for _ in ()).throw(AssertionError("must not post")))
    orch.decide_and_post(pid, "skip", store=store)
    assert store.get(pid)["status"] == "skipped"


def test_decide_and_post_timeout_auto(tmp_path, monkeypatch):
    store = orch.DistStore(str(tmp_path / "d.db"))
    pid = store.insert(video_path="v", mechanic="vote", content_angle="a",
                       layout="split_2", asset_ids=["x"], caption="c")
    monkeypatch.setattr(orch, "_do_post", lambda row: {"ok": True})
    orch.decide_and_post(pid, "timeout", store=store)
    assert store.get(pid)["status"] == "auto_posted"


def test_decide_and_post_failure_marks_failed(tmp_path, monkeypatch):
    store = orch.DistStore(str(tmp_path / "d.db"))
    pid = store.insert(video_path="v", mechanic="vote", content_angle="a",
                       layout="split_2", asset_ids=["x"], caption="c")
    monkeypatch.setattr(orch, "_do_post", lambda row: {"ok": False, "error": "boom"})
    orch.decide_and_post(pid, "approve", store=store)
    assert store.get(pid)["status"] == "failed"
