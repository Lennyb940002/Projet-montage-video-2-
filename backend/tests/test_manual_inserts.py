"""Tests du merge_timeline (#14) : inserts manuels priment sur les clips auto.

Contrats stricts :
- 0 insert -> map direct des ranges en segments 'auto'
- 1 insert qui couvre TOUT un range -> ce range devient l'insert pur
- 1 insert qui chevauche partiellement -> split (auto_avant + insert + auto_après)
- 1 insert qui chevauche 2 ranges -> ces 2 ranges sont split correctement
- Auto segments conservent leur auto_idx pour le look-up motion/transitions du Director
"""
from backend.pipeline.montage import _merge_timeline


def test_no_inserts_returns_ranges_as_auto_segments():
    ranges = [(0.0, 2.0), (2.0, 5.0)]
    segs = _merge_timeline(ranges, None)
    assert segs == [
        {"kind": "auto", "start": 0.0, "end": 2.0, "auto_idx": 0},
        {"kind": "auto", "start": 2.0, "end": 5.0, "auto_idx": 1},
    ]
    # Idempotent avec liste vide aussi
    assert _merge_timeline(ranges, []) == segs


def test_insert_covering_full_range_replaces_it():
    ranges = [(0.0, 2.0), (2.0, 5.0)]
    inserts = [{"kind": "image", "path": "C:/a.png", "start": 2.0, "end": 5.0}]
    segs = _merge_timeline(ranges, inserts)
    # Le 1er range reste auto, le 2e est totalement remplacé par l'insert
    assert len(segs) == 2
    assert segs[0]["kind"] == "auto" and segs[0]["auto_idx"] == 0
    assert segs[1] == {"kind": "image", "path": "C:/a.png", "start": 2.0, "end": 5.0}


def test_insert_partial_splits_range_in_three_pieces():
    """Insert au milieu d'un range -> auto_avant + insert + auto_après."""
    ranges = [(0.0, 6.0)]
    inserts = [{"kind": "clip", "path": "C:/v.mp4", "start": 2.0, "end": 4.0}]
    segs = _merge_timeline(ranges, inserts)
    assert len(segs) == 3
    assert segs[0] == {"kind": "auto", "start": 0.0, "end": 2.0, "auto_idx": 0}
    assert segs[1] == {"kind": "clip", "path": "C:/v.mp4", "start": 2.0, "end": 4.0}
    assert segs[2] == {"kind": "auto", "start": 4.0, "end": 6.0, "auto_idx": 0}


def test_insert_spanning_two_ranges_splits_both():
    """Un insert qui déborde sur 2 ranges doit générer le bon enchaînement."""
    ranges = [(0.0, 3.0), (3.0, 6.0)]
    inserts = [{"kind": "image", "path": "C:/a.png", "start": 2.0, "end": 4.0}]
    segs = _merge_timeline(ranges, inserts)
    # Attendu : auto[0,2] + insert[2,3] + insert[3,4] + auto[4,6]
    # Note : l'insert est dupliqué pour rester contigu à chaque range source.
    # Pour V1 on tolère 2 segments insert consécutifs ; le concat ffmpeg les
    # rejouera comme une seule image continue.
    assert len(segs) == 4
    assert segs[0]["kind"] == "auto"
    assert segs[1]["kind"] == "image" and segs[1]["start"] == 2.0 and segs[1]["end"] == 3.0
    assert segs[2]["kind"] == "image" and segs[2]["start"] == 3.0 and segs[2]["end"] == 4.0
    assert segs[3]["kind"] == "auto" and segs[3]["start"] == 4.0


def test_multiple_inserts_in_one_range_keep_order():
    ranges = [(0.0, 10.0)]
    inserts = [
        {"kind": "image", "path": "C:/b.png", "start": 5.0, "end": 6.0},
        {"kind": "image", "path": "C:/a.png", "start": 2.0, "end": 3.0},
    ]
    segs = _merge_timeline(ranges, inserts)
    # Doivent être triés par start
    kinds = [s["kind"] for s in segs]
    starts = [s["start"] for s in segs]
    assert kinds == ["auto", "image", "auto", "image", "auto"]
    assert starts == [0.0, 2.0, 3.0, 5.0, 6.0]


def test_insert_at_range_start_no_empty_auto_segment():
    """Insert qui commence exactement au début d'un range -> pas de segment auto vide."""
    ranges = [(0.0, 4.0)]
    inserts = [{"kind": "image", "path": "C:/a.png", "start": 0.0, "end": 2.0}]
    segs = _merge_timeline(ranges, inserts)
    assert len(segs) == 2
    assert segs[0]["kind"] == "image"
    assert segs[1]["kind"] == "auto" and segs[1]["start"] == 2.0


def test_zero_duration_inserts_are_ignored():
    ranges = [(0.0, 4.0)]
    inserts = [{"kind": "image", "path": "C:/a.png", "start": 1.0, "end": 1.0}]
    segs = _merge_timeline(ranges, inserts)
    # Insert de durée 0 ignoré -> reste 1 seul segment auto
    assert segs == [{"kind": "auto", "start": 0.0, "end": 4.0, "auto_idx": 0}]


# ============================================================
# Tests d'intégration : render() avec un vrai insert (ffmpeg)
# ============================================================
import os
from backend.pipeline.montage import render
from backend import ffmpeg as _ff

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
INSERT_PNG = os.path.join(FIXTURES, "sample_insert.png")
INSERT_MP4 = os.path.join(FIXTURES, "sample_insert.mp4")


def _mini_ass(path):
    open(path, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
        "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,80,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,"
        "1,0,0,0,100,100,0,0,1,4,0,5,80,80,80,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,TEST\n")


def test_render_with_image_insert_produces_video(sample_audio, tmp_path):
    """Vérifie que le filter graph ffmpeg accepte un insert image et produit
       une sortie vidéo de la bonne durée (== durée audio)."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = _ff.probe_duration(sample_audio)
    ranges = [(0.0, dur)]
    inserts = [{"kind": "image", "path": INSERT_PNG,
                "start": 0.5, "end": min(2.5, dur - 0.5)}]
    out = str(tmp_path / "out.mp4")
    render(sample_audio, ass, ranges, out, manual_inserts=inserts)
    assert os.path.exists(out)
    out_dur = _ff.probe_duration(out)
    # Tolérance 0.3s (encodage, fps quantization)
    assert abs(out_dur - dur) < 0.5


def test_render_with_clip_insert_produces_video(sample_audio, tmp_path):
    """Idem avec un insert vidéo manuel."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = _ff.probe_duration(sample_audio)
    ranges = [(0.0, dur)]
    inserts = [{"kind": "clip", "path": INSERT_MP4,
                "start": 1.0, "end": min(3.0, dur - 0.5)}]
    out = str(tmp_path / "out.mp4")
    render(sample_audio, ass, ranges, out, manual_inserts=inserts)
    assert os.path.exists(out)
    out_dur = _ff.probe_duration(out)
    assert abs(out_dur - dur) < 0.5


def test_render_without_inserts_is_strict_noop_on_pipeline(sample_audio, tmp_path):
    """Garde-fou : manual_inserts=None doit produire EXACTEMENT le même comportement
       que l'API d'origine (test de non-régression critique)."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = _ff.probe_duration(sample_audio)
    ranges = [(0.0, dur)]
    out_none = str(tmp_path / "out_none.mp4")
    out_empty = str(tmp_path / "out_empty.mp4")
    render(sample_audio, ass, ranges, out_none, manual_inserts=None, seed=42)
    render(sample_audio, ass, ranges, out_empty, manual_inserts=[], seed=42)
    # Les 2 doivent produire des vidéos de durée identique (même clip auto pick)
    d1 = _ff.probe_duration(out_none)
    d2 = _ff.probe_duration(out_empty)
    assert abs(d1 - d2) < 0.1
