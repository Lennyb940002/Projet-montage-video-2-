from backend.pipeline.transcribe import transcribe, Word

def test_transcribe_returns_words(sample_audio):
    words, duration = transcribe(sample_audio)
    assert duration > 5
    assert len(words) > 5
    assert isinstance(words[0], Word)
    assert all(w.start <= w.end for w in words)
    # mots couvrent globalement l'audio
    assert words[-1].end <= duration + 0.5
    # texte plausible
    joined = " ".join(w.text for w in words).lower()
    assert "montre" in joined
