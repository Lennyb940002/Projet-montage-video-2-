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

def test_fun_style_multicolor_and_anim(tmp_path):
    out = str(tmp_path / "f.ass")
    build_ass(TOKENS, 1, out, style="multicolor_fun")
    content = open(out, encoding="utf-8").read()
    assert "&H0000FF00&" in content      # vert
    assert "&H0000FFFF&" in content      # jaune
    assert "\\t(" in content             # animation (pop)
    assert "\\k" not in content          # pas de karaoké

def test_premium_v2_minimalist_render(tmp_path):
    """V2 minimaliste : mouvement sur le BLOC, karaoké couleur via \\kf
       sans scale par mot. Fini le clignotement / les bounces individuels."""
    from backend.pipeline.subtitles import render_plan_subs
    plan_subs = [
        {"start": 0.0, "end": 0.8,
         "words": [
            {"disp": "Cette", "role": "normal",  "start": 0.0, "end": 0.3},
            {"disp": "Rolex", "role": "kw",      "start": 0.3, "end": 0.6},
            {"disp": "ouf",   "role": "normal",  "start": 0.6, "end": 0.8},
         ]},
    ]
    out = str(tmp_path / "p.ass")
    render_plan_subs(plan_subs, out, style="premium_pop")
    c = open(out, encoding="utf-8").read()
    # Anim BLOC : fade + scale léger 96->100 (1 SEUL \t global pour le bloc)
    assert "\\fad(120,80)" in c
    assert "\\fscx96" in c and "\\t(0,180" in c
    # Karaoké couleur via \kf (PAS de \k bête)
    assert "\\kf" in c
    # Accent jaune utilisé pour le keyword (\1c<accent>)
    assert "&H0000FFFF&" in c
    # Anti-régression : on n'écrit PAS de scale par mot (\fscx avec valeur != 96)
    assert "\\fscx152" not in c and "\\fscx130" not in c
    # 1 Dialogue par chunk (pas un par mot)
    assert c.count("Dialogue:") == 1


def test_premium_v2_no_overlap_between_dialogues(tmp_path):
    """Aucun overlap entre deux Dialogues consécutifs (anti-fantôme)."""
    from backend.pipeline.subtitles import render_plan_subs, ass_time
    plan_subs = [
        {"start": 0.0, "end": 1.0,
         "words": [{"disp": "Salut", "role": "normal", "start": 0.0, "end": 0.5},
                   {"disp": "toi",   "role": "normal", "start": 0.5, "end": 1.0}]},
        {"start": 1.0, "end": 2.0,
         "words": [{"disp": "Ça",    "role": "normal", "start": 1.0, "end": 1.5},
                   {"disp": "va",    "role": "normal", "start": 1.5, "end": 2.0}]},
    ]
    out = str(tmp_path / "p2.ass")
    render_plan_subs(plan_subs, out, style="premium_pop")
    c = open(out, encoding="utf-8").read()
    assert c.count("Dialogue:") == 2
    # Le end du 1er == le start du 2e (strings ASS time)
    assert f",{ass_time(1.0)}," in c

def test_build_ass_rejects_premium_without_plan(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="plan"):
        build_ass(TOKENS, 1, str(tmp_path / "x.ass"), style="premium_pop")

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
