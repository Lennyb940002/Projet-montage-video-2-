from backend.pipeline.align import tokenize, align
from backend.pipeline.transcribe import Word

def test_tokenize_sentences_and_symbols():
    toks, n = tokenize("Salut le monde. 90 % des gens ?")
    assert n == 2  # deux phrases
    assert toks[0]["disp"].lower() == "salut"
    # le symbole % est fusionné au mot précédent, pas un token isolé
    assert any("%" in t["disp"] for t in toks)

def test_align_transfers_timings_exact_match():
    words = [Word("salut", 0.0, 0.5, 0.9), Word("monde", 0.5, 1.0, 0.9)]
    toks, n = tokenize("Salut monde.")
    align(toks, words)
    assert toks[0]["start"] == 0.0
    assert toks[1]["start"] == 0.5
    # monotonie
    assert toks[0]["start"] <= toks[1]["start"]

def test_align_interpolates_missing():
    # whisper n'a qu'un mot, le texte en a 3 -> interpolation, pas de None
    words = [Word("monde", 1.0, 1.4, 0.9)]
    toks, n = tokenize("salut le monde")
    align(toks, words)
    assert all(t["start"] is not None for t in toks)
    assert all(t["end"] >= t["start"] for t in toks)
