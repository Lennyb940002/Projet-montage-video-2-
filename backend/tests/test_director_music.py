from backend.pipeline.director import (
    _score_music_category, _voice_active_events, _pre_cta_gap_event,
)


def _kw(label, start=1.0, imp="high"):
    return {"type": "keyword", "label": label,
            "start": start, "end": start + 0.4, "importance": imp}


# ---------------- Scoring catégorie ----------------

def test_score_hype_wins_on_ctas_and_numbers():
    events = [_kw("Écris", imp="high"), _kw("commente", imp="high"),
              _kw("200€", imp="high"), _kw("3", imp="high")]
    res = _score_music_category(events, duration=15.0)
    assert res["category"] == "hype"
    assert res["confidence"] >= 0.60
    assert res["fallback_used"] is False
    # Reasons humaines présentes
    assert any("CTA" in r or "chiffres" in r or "duration" in r for r in res["reason"])


def test_score_luxury_wins_on_brand_superlative():
    events = [_kw("Rolex"), _kw("incroyable")]
    res = _score_music_category(events, duration=25.0)
    assert res["category"] == "luxury"
    assert res["fallback_used"] is False
    assert "brand detected" in res["reason"]
    assert "superlative detected" in res["reason"]


def test_score_includes_detailed_scores_for_both_categories():
    """Le debug DOIT contenir les scores des deux catégories pour traçabilité."""
    events = [_kw("Rolex"), _kw("incroyable")]
    res = _score_music_category(events, duration=25.0)
    assert "scores" in res
    assert "luxury" in res["scores"] and "hype" in res["scores"]
    assert isinstance(res["scores"]["luxury"], float)
    assert isinstance(res["scores"]["hype"], float)
    # Luxury doit dépasser Hype dans ce cas
    assert res["scores"]["luxury"] > res["scores"]["hype"]


def test_score_fallback_when_low_confidence():
    """Aucun signal -> fallback Luxury."""
    res = _score_music_category([], duration=15.0)
    assert res["category"] == "luxury"
    assert res["reason"] == ["low confidence fallback"]
    assert res["fallback_used"] is True
    # Mais les scores détaillés sont quand même présents
    assert "scores" in res


def test_score_fallback_preserves_winner_scores():
    """Même en fallback, on conserve les scores calculés pour comprendre le pourquoi."""
    res = _score_music_category([], duration=15.0)
    assert res["scores"]["luxury"] >= 0.0
    assert res["scores"]["hype"] >= 0.0


# ---------------- Helpers events ----------------

def test_voice_active_events_from_tokens():
    tokens = [{"disp": "Un", "start": 0.0, "end": 0.3, "sent": 0},
              {"disp": "mot", "start": 0.4, "end": 0.7, "sent": 0},
              {"disp": "ici", "start": 3.0, "end": 3.3, "sent": 1}]
    events = _voice_active_events(tokens, gap_threshold=1.0)
    assert all(e["type"] == "voice_active" for e in events)
    assert events[0]["start"] == 0.0 and events[0]["end"] >= 0.7
    assert events[-1]["start"] >= 3.0


def test_voice_active_empty_tokens():
    assert _voice_active_events([]) == []


def test_pre_cta_gap_from_cta_keyword():
    events = [{"type": "keyword", "label": "Écris",
               "start": 12.0, "end": 12.4, "importance": "high"}]
    gap = _pre_cta_gap_event(events, gap_dur=1.2)
    assert gap is not None
    assert abs(gap["end"] - 12.0) < 1e-9
    assert abs(gap["start"] - 10.8) < 1e-9
    assert gap["type"] == "pre_cta_gap"
    assert gap["importance"] == "high"


def test_pre_cta_gap_none_when_no_cta():
    assert _pre_cta_gap_event([{"type": "keyword", "label": "Rolex",
                                "start": 1.0, "end": 1.4, "importance": "high"}]) is None


def test_pre_cta_gap_clamps_at_zero():
    """Si le CTA est tôt, le gap ne descend pas sous 0."""
    events = [{"type": "keyword", "label": "Écris",
               "start": 0.5, "end": 0.9, "importance": "high"}]
    gap = _pre_cta_gap_event(events, gap_dur=1.2)
    assert gap["start"] == 0.0
