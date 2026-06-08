from backend.pipeline.detect import find_retakes, low_confidence, detect, long_pauses
from backend.pipeline.transcribe import Word

def W(t, s, e, p=0.99):
    return Word(t, s, e, p)

def test_find_retakes_exact_repeat():
    # "voici les trois montres voici les trois montres" -> 1ère occurrence à couper
    txt = "voici les trois montres voici les trois montres et voila".split()
    words = [W(t, i*0.5, i*0.5+0.4) for i, t in enumerate(txt)]
    r = find_retakes(words)
    assert len(r) == 1
    assert r[0]["i1"] == 0 and r[0]["i2"] == 4   # supprime la 1ère occurrence (mots 0..3)
    assert r[0]["start"] == words[0].start

def test_find_retakes_none():
    words = [W(t, i*0.5, i*0.5+0.4) for i, t in enumerate("bonjour tout le monde ca va".split())]
    assert find_retakes(words) == []

def test_low_confidence():
    words = [W("bon", 0, 0.4, 0.95), W("zzz", 0.4, 0.8, 0.20), W("jour", 0.8, 1.2, 0.9)]
    lc = low_confidence(words, threshold=0.5)
    assert lc == [1]

def test_find_retakes_fuzzy():
    a = "je te présente la daytona rainbow or".split()
    b = "je te présente la daytona rainbow rose".split()
    txt = a + b + ["et", "voila"]
    words = [W(t, i*0.4, i*0.4+0.3) for i, t in enumerate(txt)]
    assert len(find_retakes(words)) >= 1

def test_low_confidence_relative():
    words = [W("a", 0, .3, .95), W("b", .3, .6, .96), W("c", .6, .9, .2), W("d", .9, 1.2, .94)]
    lc = low_confidence(words)          # sans seuil -> relatif
    assert 2 in lc and 0 not in lc

def test_long_pauses():
    words = [W("a", 0, .4), W("b", .5, .9), W("c", 2.0, 2.4)]
    p = long_pauses(words, min_gap=0.7)
    assert len(p) == 1 and abs(p[0]["start"] - 0.9) < 1e-6

def test_detect_has_pauses():
    words = [W("a", 0, .3, .9), W("b", 2.0, 2.3, .9)]
    d = detect(words)
    assert "pauses" in d and len(d["pauses"]) == 1

def test_detect_shape():
    words = [W("a", 0, .3, .9), W("b", .3, .6, .2)]
    d = detect(words)
    assert "retakes" in d and "lowconf" in d
