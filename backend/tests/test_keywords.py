from backend.pipeline import keywords

def _toks(words):
    return [{"disp": w, "start": i*0.4, "end": i*0.4+0.3, "sent": 0} for i, w in enumerate(words)]

def test_mark_flags_keywords():
    toks = keywords.mark(_toks(["Cette", "Rolex", "à", "200€", "est", "incroyable", "la"]))
    flags = {t["disp"]: t["kw"] for t in toks}
    assert flags["Rolex"] and flags["200€"] and flags["incroyable"]
    assert not flags["Cette"] and not flags["la"]
