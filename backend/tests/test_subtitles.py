from backend.pipeline.subtitles import build_ass, ass_time

def test_ass_time_format():
    assert ass_time(0) == "0:00:00.00"
    assert ass_time(61.5) == "0:01:01.50"

def test_build_ass(tmp_path):
    tokens = [
        {"disp": "Salut", "sent": 0, "start": 0.0, "end": 0.4},
        {"disp": "le", "sent": 0, "start": 0.4, "end": 0.6},
        {"disp": "monde", "sent": 0, "start": 0.6, "end": 1.0},
    ]
    out = str(tmp_path / "s.ass")
    build_ass(tokens, 1, out)
    content = open(out, encoding="utf-8").read()
    # en-tête AVEC champ Name (sinon bug virgule)
    assert "Format: Layer, Start, End, Style, Name," in content
    # karaoké \k présent et texte en MAJUSCULES
    assert "\\k" in content and "SALUT" in content
    # pas de double Dialogue par mot : 1 ligne par bloc
    assert content.count("Dialogue:") == 1
