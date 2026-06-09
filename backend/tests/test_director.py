from backend.pipeline.director import build_plan

def _toks(words, sent=None):
    """Helper : crée des tokens espacés de 0.4s. sent peut être une liste."""
    out = []
    for i, w in enumerate(words):
        out.append({"disp": w, "start": i * 0.4, "end": i * 0.4 + 0.3,
                    "sent": sent[i] if sent else 0})
    return out

def test_plan_has_required_keys():
    tokens = _toks(["A", "B"])
    plan = build_plan([], tokens, 1, [(0.0, 1.0)], 1.0)
    # subtitles/motion/transitions sont toujours présents et structurés ;
    # music s'ajoute depuis T5 (Music V1) — peut être None si pas de banque.
    assert {"subtitles", "motion", "transitions", "music"} <= set(plan.keys())

def test_motion_v1_one_zoom_clip_per_range():
    tokens = _toks(["A", "B", "C"])
    ranges = [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)]
    plan = build_plan([], tokens, 1, ranges, 3.0)
    zooms = [m for m in plan["motion"] if m["kind"] == "zoom_clip"]
    assert len(zooms) == 3
    assert [z["clip_index"] for z in zooms] == [0, 1, 2]
    # rotation
    assert len({z["zoom"] for z in zooms}) > 1

def test_motion_punch_on_keyword_event():
    tokens = _toks(["Voici", "Rolex", "incroyable"])
    events = [{"type": "keyword", "label": "Rolex", "start": 0.4, "end": 0.7, "importance": "high"}]
    ranges = [(0.0, 1.0), (1.0, 2.0)]
    plan = build_plan(events, tokens, 1, ranges, 2.0)
    punches = [m for m in plan["motion"] if m["kind"] == "punch"]
    shakes = [m for m in plan["motion"] if m["kind"] == "shake"]
    assert len(punches) == 1 and punches[0]["clip_index"] == 0
    assert abs(punches[0]["at_local"] - 0.4) < 1e-9
    assert len(shakes) == 1  # importance=high -> shake

def test_transitions_length_preserving_fade_in_per_cut():
    tokens = _toks(["A", "B"])
    ranges = [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)]
    plan = build_plan([], tokens, 1, ranges, 3.0)
    assert all(t["kind"] == "fade_in" for t in plan["transitions"])
    assert [t["clip_index"] for t in plan["transitions"]] == [1, 2]

def test_transitions_zoom_punch_in_on_high_keyword_at_clip_start():
    """Si un keyword 'high' tombe dans les 0.5s d'entrée d'un clip,
    le Director choisit zoom_punch_in au lieu de fade_in."""
    tokens = _toks(["A", "B"])
    events = [
        {"type": "keyword", "label": "Rolex", "start": 1.1, "end": 1.4, "importance": "high"},
    ]
    ranges = [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)]
    plan = build_plan(events, tokens, 1, ranges, 3.0)
    by_clip = {t["clip_index"]: t for t in plan["transitions"]}
    assert by_clip[1]["kind"] == "zoom_punch_in"   # keyword à 1.1s = début du clip 1
    assert by_clip[2]["kind"] == "fade_in"         # pas de keyword au début du clip 2

def test_subtitles_roles_assigned_correctly():
    tokens = _toks(["Cette", "Rolex", "incroyable"])
    events = [
        {"type": "keyword", "label": "Rolex",      "start": 0.4, "end": 0.7, "importance": "high"},
        {"type": "keyword", "label": "incroyable", "start": 0.8, "end": 1.1, "importance": "high"},
    ]
    plan = build_plan(events, tokens, 1, [(0.0, 2.0)], 2.0)
    subs = plan["subtitles"]
    assert len(subs) == 3  # une SubLine par mot actif
    # Mot 1 actif (Cette) : Rolex en kw_idle, incroyable en kw_idle
    roles_0 = [w["role"] for w in subs[0]["words"]]
    assert roles_0 == ["active", "kw_idle", "kw_idle"]
    # Mot 2 actif (Rolex, kw)
    roles_1 = [w["role"] for w in subs[1]["words"]]
    assert roles_1 == ["normal", "kw_active", "kw_idle"]
    # Mot 3 actif (incroyable, kw)
    roles_2 = [w["role"] for w in subs[2]["words"]]
    assert roles_2 == ["normal", "kw_idle", "kw_active"]

def test_plan_is_json_serializable():
    import json
    tokens = _toks(["Cette", "Rolex"])
    events = [{"type": "keyword", "label": "Rolex", "start": 0.4, "end": 0.7, "importance": "high"}]
    plan = build_plan(events, tokens, 1, [(0.0, 1.0)], 1.0)
    s = json.dumps(plan)
    assert "subtitles" in s and "motion" in s and "transitions" in s
