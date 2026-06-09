"""T6 — music_engine.build() : transformation plan['music'] -> fragment ffmpeg.

Purement exécutif : pas de logique métier ; itère sur beds[] et accents[].
"""
import pytest

from backend.pipeline import music_engine


# ---------------- No-op cases ----------------

def test_no_op_when_music_none():
    out = music_engine.build(None, voice_label="vmix", base_input_idx=2)
    assert out["extra_inputs"] == []
    assert out["filter_str"] == ""
    assert out["out_label"] == "vmix"
    assert out["beds_processed"] == 0
    assert out["accents_processed"] == 0


def test_no_op_when_no_beds():
    out = music_engine.build({"beds": [], "accents": []}, "vmix", 2)
    assert out["extra_inputs"] == []
    assert out["filter_str"] == ""
    assert out["out_label"] == "vmix"
    assert out["beds_processed"] == 0


# ---------------- 1 bed (cas V1) ----------------

def _bed(track="/abs/t.mp3", dur=13.5, gaps=None):
    return {
        "track": track, "trim_start": 0.0, "start": 0.0, "duration": dur,
        "base_gain_dB": -22.0, "fade_in_ms": 800, "fade_out_ms": 1200,
        "duck": {
            "mode": "sidechain", "ratio": 6.0, "threshold_dB": -28,
            "attack_ms": 8, "release_ms": 280, "depth_dB": -12.0, "side": "voice",
        },
        "gaps": gaps or [],
    }


def test_build_one_bed_returns_filter_and_input():
    bed = _bed(gaps=[{"start": 11.0, "end": 12.0, "fade_out_ms": 250, "fade_in_ms": 200}])
    out = music_engine.build({"beds": [bed], "accents": [], "mix": {"target_lufs": -16.0}},
                              voice_label="vmix", base_input_idx=3)
    assert out["extra_inputs"] == ["/abs/t.mp3"]
    f = out["filter_str"]
    assert "atrim" in f
    assert "volume=-22" in f or "volume=-22.0" in f
    assert "afade=t=in" in f and "afade=t=out" in f
    assert "sidechaincompress" in f
    # gap entre 11.0 et 12.0 -> volume=0 enable=between(t,...)
    assert "between(t,11" in f
    # label de sortie = mix final voix+musique
    assert out["out_label"] == "mout"
    assert out["beds_processed"] == 1


def test_build_uses_correct_input_index():
    """L'input ffmpeg [3:a] doit apparaître quand base_input_idx=3."""
    out = music_engine.build({"beds": [_bed()], "accents": []}, "vmix", 3)
    assert "[3:a]" in out["filter_str"]


def test_build_with_no_gaps_skips_gap_filter():
    out = music_engine.build({"beds": [_bed(gaps=[])], "accents": []}, "vmix", 2)
    assert "between(t" not in out["filter_str"]


# ---------------- Multi-beds (garde-fou : boucle dès V1) ----------------

def test_build_iterates_over_multiple_beds():
    """Garde-fou : même si V1 ne génère qu'un bed, le moteur DOIT itérer
    sur beds[] (préparation intro calme / montée / CTA final futurs)."""
    bed_a = _bed(track="/abs/a.mp3", dur=5.0)
    bed_a["start"] = 0.0
    bed_b = _bed(track="/abs/b.mp3", dur=8.0)
    bed_b["start"] = 5.0
    plan = {"beds": [bed_a, bed_b], "accents": [], "mix": {"target_lufs": -16.0}}
    out = music_engine.build(plan, voice_label="vmix", base_input_idx=4)
    assert out["extra_inputs"] == ["/abs/a.mp3", "/abs/b.mp3"]
    assert out["beds_processed"] == 2
    # Les deux beds ont leur input
    assert "[4:a]" in out["filter_str"]
    assert "[5:a]" in out["filter_str"]
    # Deux sidechain (un par bed)
    assert out["filter_str"].count("sidechaincompress") == 2


def test_build_accents_processed_counted():
    """accents=[] en V1 -> compteur à 0 (futur : >0)."""
    out = music_engine.build({"beds": [_bed()], "accents": []}, "vmix", 2)
    assert out["accents_processed"] == 0


# ---------------- Robustesse ----------------

def test_build_filter_is_single_string_separated_by_semicolons():
    """Format attendu par filter_complex : chaînes liées par ';'."""
    out = music_engine.build({"beds": [_bed()], "accents": []}, "vmix", 2)
    # le filter_str doit pouvoir être donné tel quel à `-filter_complex`
    assert ";" in out["filter_str"]
    # pas de ';;' (chaîne vide entre)
    assert ";;" not in out["filter_str"]
