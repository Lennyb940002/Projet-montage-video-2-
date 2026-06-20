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

def test_subtitles_v2_one_line_per_chunk_with_word_timings():
    """V2 minimaliste : 1 SubLine par CHUNK (pas par mot), chaque mot porte
       ses propres start/end + role binaire (kw|normal). Le renderer fait le
       karaoké via \\kf sans redessiner la ligne — fin du clignotement."""
    tokens = _toks(["Cette", "Rolex", "incroyable"])
    events = [
        {"type": "keyword", "label": "Rolex",      "start": 0.4, "end": 0.7, "importance": "high"},
        {"type": "keyword", "label": "incroyable", "start": 0.8, "end": 1.1, "importance": "high"},
    ]
    plan = build_plan(events, tokens, 1, [(0.0, 2.0)], 2.0)
    subs = plan["subtitles"]
    # 1 chunk de 3 mots -> 1 seule SubLine (avant : 3, qui causait le clignotement)
    assert len(subs) == 1
    roles = [w["role"] for w in subs[0]["words"]]
    assert roles == ["normal", "kw", "kw"]
    # Chaque mot porte start/end pour le karaoké \kf
    for w in subs[0]["words"]:
        assert "start" in w and "end" in w
        assert w["end"] > w["start"]


def test_subtitles_v2_no_overlap_between_lines():
    """Anti-fantôme : end d'une ligne == start de la suivante (strict),
       jamais d'overlap qui ferait persister une vieille phrase à l'écran."""
    # 6 mots -> 2 chunks de 3 (MAXWORDS=3)
    tokens = _toks(["un", "deux", "trois", "quatre", "cinq", "six"])
    plan = build_plan([], tokens, 1, [(0.0, 3.0)], 3.0)
    subs = plan["subtitles"]
    assert len(subs) == 2
    # end de la 1re == start de la 2e (anti-overlap strict)
    assert subs[0]["end"] == subs[1]["start"]

def test_plan_is_json_serializable():
    import json
    tokens = _toks(["Cette", "Rolex"])
    events = [{"type": "keyword", "label": "Rolex", "start": 0.4, "end": 0.7, "importance": "high"}]
    plan = build_plan(events, tokens, 1, [(0.0, 1.0)], 1.0)
    s = json.dumps(plan)
    assert "subtitles" in s and "motion" in s and "transitions" in s
