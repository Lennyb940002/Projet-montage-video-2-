from backend.pipeline.director import build_plan

def test_plan_shape():
    tokens = [{"disp": "Rolex", "start": 1.0, "end": 1.4, "sent": 0, "kw": True},
              {"disp": "belle", "start": 1.4, "end": 1.8, "sent": 0, "kw": False}]
    ranges = [(0.0, 3.0), (3.0, 6.0)]
    plan = build_plan(tokens, 2, ranges, 6.0)
    assert any(m["kind"] == "kenburns" for m in plan["motion"])
    assert any(m["kind"] == "punch" and abs(m["start"] - 1.0) < 1e-6 for m in plan["motion"])
    assert len(plan["transitions"]) == 1 and abs(plan["transitions"][0]["at"] - 3.0) < 1e-6
