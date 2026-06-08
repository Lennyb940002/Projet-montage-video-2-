from backend.pipeline import keywords

def _toks(words):
    return [{"disp": w, "start": i * 0.4, "end": i * 0.4 + 0.3, "sent": 0}
            for i, w in enumerate(words)]

def test_detect_events_returns_normalized_events():
    ev = keywords.detect_events(_toks(["Cette", "Rolex", "à", "200€", "est", "incroyable", "la"]))
    labels = {e["label"]: e for e in ev}
    assert {"Rolex", "200€", "incroyable"} <= set(labels.keys())
    assert all(e["type"] == "keyword" for e in ev)
    assert all({"start", "end", "importance"} <= set(e.keys()) for e in ev)
    assert labels["Rolex"]["importance"] == "high"
    assert labels["200€"]["importance"] == "high"
    assert labels["incroyable"]["importance"] == "high"

def test_detect_events_ignores_neutral_words():
    ev = keywords.detect_events(_toks(["la", "bonjour", "table"]))
    assert ev == []

def test_event_keeps_token_timing():
    ev = keywords.detect_events(_toks(["Cette", "Rolex"]))
    rolex = ev[0]
    assert rolex["start"] == 0.4 and abs(rolex["end"] - 0.7) < 1e-9
