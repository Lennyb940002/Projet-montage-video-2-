import backend.distribution.caption_seo as cs


def test_fallback_when_no_key(monkeypatch):
    monkeypatch.setattr(cs, "_gemini_key", lambda: None)
    cap, tags = cs.build_caption(mechanic="comparison",
                                 model_names=["Seiko Daytona Or rose", "Seiko Daytona Saphir"],
                                 hook="Laquelle ?")
    assert isinstance(cap, str) and cap
    assert 1 <= len(tags) <= 2
    assert all(t.startswith("#") for t in tags)


def test_gemini_path(monkeypatch):
    monkeypatch.setattr(cs, "_gemini_key", lambda: "KEY")
    def fake_call(prompt, key):
        return "Decouvre la Seiko Daytona Or rose vs Saphir\n\n#montre #seiko"
    monkeypatch.setattr(cs, "_gemini_generate", fake_call)
    cap, tags = cs.build_caption(mechanic="comparison",
                                 model_names=["Seiko Daytona Or rose"], hook="A ou B ?")
    assert "Seiko" in cap
    assert len(tags) <= 2 and all(t.startswith("#") for t in tags)


def test_gemini_error_falls_back(monkeypatch):
    monkeypatch.setattr(cs, "_gemini_key", lambda: "KEY")
    def boom(prompt, key): raise RuntimeError("gemini down")
    monkeypatch.setattr(cs, "_gemini_generate", boom)
    cap, tags = cs.build_caption(mechanic="vote", model_names=["X"], hook="Vote")
    assert cap and 1 <= len(tags) <= 2
