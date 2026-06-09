"""Bug : Whisper sépare les apostrophes (renvoie 'Aujourd' puis '\\'hui,').
La reconstruction naïve " ".join(...) produit `Aujourd 'hui` dans les sous-titres.

Fix : helper `_glue_punct` qui recolle les morceaux commençant par apostrophe
ou ponctuation au mot précédent.
"""
from backend.service import _glue_punct
from backend.pipeline.transcribe import Word


def test_glue_apostrophe_at_word_start():
    """`Aujourd` + `'hui,` -> `Aujourd'hui,`"""
    out = _glue_punct(["Aujourd", "'hui,", "j", "'ai", "un", "défi"])
    assert out == ["Aujourd'hui,", "j'ai", "un", "défi"]


def test_glue_handles_leading_quotes():
    """Variantes UTF : apostrophe courbe (' '0x2019')"""
    out = _glue_punct(["N", "’est", "qu", "’une"])
    assert out == ["N’est", "qu’une"]


def test_glue_keeps_normal_words_unchanged():
    out = _glue_punct(["trois", "montres,", "trois", "styles."])
    assert out == ["trois", "montres,", "trois", "styles."]


def test_glue_handles_lonely_punct():
    """Un morceau qui est SEULEMENT de la ponctuation s'attache au précédent."""
    out = _glue_punct(["Voila", ".", "et", "puis"])
    assert out == ["Voila.", "et", "puis"]


def test_glue_words_to_transcript_from_whisper_words():
    """Vrai cas : whisper renvoie des Word avec apostrophes séparées."""
    from backend.service import _transcript_from_words
    words = [
        Word("Aujourd", 0.0, 0.3, 0.99),
        Word("'hui,", 0.3, 0.5, 1.0),
        Word("j", 0.6, 0.7, 0.99),
        Word("'ai", 0.7, 0.9, 0.99),
        Word("un", 0.9, 1.1, 0.99),
        Word("défi", 1.1, 1.5, 0.99),
    ]
    assert _transcript_from_words(words) == "Aujourd'hui, j'ai un défi"
