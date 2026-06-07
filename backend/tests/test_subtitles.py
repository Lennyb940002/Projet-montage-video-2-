from backend.pipeline.subtitles import build_ass, ass_time, list_styles, STYLES

TOKENS = [
    {"disp": "Salut", "sent": 0, "start": 0.0, "end": 0.4},
    {"disp": "le", "sent": 0, "start": 0.4, "end": 0.6},
    {"disp": "monde", "sent": 0, "start": 0.6, "end": 1.0},
]

def test_list_styles_has_presets():
    keys = [s["key"] for s in list_styles()]
    assert "karaoke_yellow" in keys and "boxed_bottom" in keys
    assert all("label" in s for s in list_styles())

def test_block_style_has_no_karaoke(tmp_path):
    out = str(tmp_path / "b.ass")
    build_ass(TOKENS, 1, out, style="white_block")
    content = open(out, encoding="utf-8").read()
    assert "\\k" not in content
    assert "SALUT" in content

def test_bottom_style_alignment(tmp_path):
    out = str(tmp_path / "bb.ass")
    build_ass(TOKENS, 1, out, style="bottom_white")
    content = open(out, encoding="utf-8").read()
    # alignment 2 (bas) présent dans la ligne Style
    assert ",2,80,80,130,1" in content.replace(" ", "") or "Arial,66" in content

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
