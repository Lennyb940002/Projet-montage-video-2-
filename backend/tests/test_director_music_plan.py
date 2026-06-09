"""T5 — _decide_music + _compute_quality_score + build_plan["music"]"""
import json
import os

from backend import ffmpeg
from backend.pipeline.director import (
    _decide_music, _compute_quality_score, build_plan,
)


def _mk_track(path, dur=60):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", f"sine=frequency=440:duration={dur}",
                "-af", "volume=-12dB", path])


def _kw(label, start=1.0, imp="high"):
    return {"type": "keyword", "label": label,
            "start": start, "end": start + 0.4, "importance": imp}


# ============== _decide_music ==============

def test_decide_music_returns_full_schema(tmp_path):
    """Plan complet : beds[0], accents=[], mix, debug avec toutes les clés."""
    (tmp_path / "Luxury").mkdir()
    _mk_track(str(tmp_path / "Luxury" / "a.mp3"))
    _mk_track(str(tmp_path / "Luxury" / "b.mp3"))
    _mk_track(str(tmp_path / "Luxury" / "c.mp3"))

    # Rolex + superlatif + duration >= 20 -> 0.85 score Luxury (au-dessus du seuil 0.60)
    tokens = [{"disp": "Rolex", "start": 1.0, "end": 1.4, "sent": 0},
              {"disp": "incroyable", "start": 2.0, "end": 2.6, "sent": 0}]
    events = [_kw("Rolex"), _kw("incroyable")]
    m = _decide_music(events, tokens, n_sent=1, ranges=[(0.0, 22.0)],
                      duration=22.0, music_root=str(tmp_path), rng_seed=42)

    # Top-level
    assert set(m.keys()) == {"beds", "accents", "mix", "debug"}
    assert m["accents"] == []
    assert m["mix"]["voice_priority"] is True
    assert m["mix"]["target_lufs"] == -16.0

    # beds[0]
    assert len(m["beds"]) == 1
    bed = m["beds"][0]
    assert bed["category"] == "luxury"
    assert bed["track"].endswith(".mp3")
    assert bed["base_gain_dB"] == -22.0     # config V1 par défaut
    assert bed["fade_in_ms"] == 800
    assert bed["fade_out_ms"] == 1200
    assert bed["duration"] == 22.0
    assert bed["duck"]["mode"] == "sidechain"
    assert bed["duck"]["depth_dB"] == -12.0
    assert bed["duck"]["side"] == "voice"
    assert bed["gaps"] == []    # pas de CTA détecté dans les events

    # debug complet et explicable
    d = m["debug"]
    for k in ("category", "confidence", "reason", "fallback_used",
              "signals", "scores", "track",
              "lufs_voice", "lufs_music_source",
              "lufs_music_at_base", "lufs_final_target", "lufs_final_actual",
              "duck_depth_dB_requested", "duck_depth_dB_effective",
              "voice_dominance_dB", "cta_detected", "gaps",
              "auto_fix_applied", "warnings", "music_quality_score"):
        assert k in d, f"debug missing key: {k}"

    assert d["cta_detected"] is False
    assert d["fallback_used"] is False
    assert d["lufs_final_target"] == -16.0
    # JSON-sérialisable
    s = json.dumps(m, ensure_ascii=False)
    assert '"beds"' in s and '"accents"' in s and '"scores"' in s


def test_decide_music_with_cta_creates_gap(tmp_path):
    (tmp_path / "Hype").mkdir()
    for n in ("a.mp3", "b.mp3", "c.mp3"):
        _mk_track(str(tmp_path / "Hype" / n))

    tokens = [
        {"disp": "Achète", "start": 1.0, "end": 1.3, "sent": 0},
        {"disp": "200€", "start": 1.4, "end": 1.7, "sent": 0},
        {"disp": "Écris", "start": 12.0, "end": 12.4, "sent": 1},
    ]
    events = [_kw("Écris", start=12.0), _kw("200€", start=1.4), _kw("3", start=2.0)]
    m = _decide_music(events, tokens, n_sent=2, ranges=[(0.0, 14.0)],
                      duration=14.0, music_root=str(tmp_path), rng_seed=1)

    # Gap pré-CTA présent
    bed = m["beds"][0]
    assert len(bed["gaps"]) == 1
    g = bed["gaps"][0]
    assert abs(g["end"] - 12.0) < 1e-9
    assert abs(g["start"] - 10.8) < 1e-9   # 12.0 - 1.2
    assert g["fade_out_ms"] == 250
    assert g["fade_in_ms"] == 200

    assert m["debug"]["cta_detected"] is True


def test_decide_music_none_when_empty_library(tmp_path):
    """Banque vide -> Director renvoie None (no-op aval, garde-fou)."""
    m = _decide_music([], [], 0, [(0.0, 5.0)], 5.0,
                      music_root=str(tmp_path))
    assert m is None


def test_decide_music_falls_back_to_other_category_if_chosen_empty(tmp_path):
    """Si Hype choisi mais vide, bascule sur Luxury (cohérence : on a une musique)."""
    # Seul Luxury rempli
    (tmp_path / "Luxury").mkdir()
    for n in ("a.mp3", "b.mp3", "c.mp3"):
        _mk_track(str(tmp_path / "Luxury" / n))

    # Events qui poussent vers Hype
    events = [_kw("Écris"), _kw("commente"), _kw("200€"), _kw("3")]
    tokens = [{"disp": "Voila", "start": 0.0, "end": 0.3, "sent": 0}]
    m = _decide_music(events, tokens, 1, [(0.0, 14.0)], 14.0,
                      music_root=str(tmp_path), rng_seed=0)

    # Catégorie effective basculée sur Luxury (le seul rempli)
    assert m["beds"][0]["category"] == "luxury"
    assert any("swap" in r for r in m["debug"]["reason"])


def test_decide_music_deterministic_with_seed(tmp_path):
    (tmp_path / "Luxury").mkdir()
    for n in ("a.mp3", "b.mp3", "c.mp3"):
        _mk_track(str(tmp_path / "Luxury" / n))
    events = [_kw("Rolex")]
    tokens = [{"disp": "Rolex", "start": 1.0, "end": 1.4, "sent": 0}]
    m1 = _decide_music(events, tokens, 1, [(0.0, 14.0)], 14.0,
                       music_root=str(tmp_path), rng_seed=42)
    m2 = _decide_music(events, tokens, 1, [(0.0, 14.0)], 14.0,
                       music_root=str(tmp_path), rng_seed=42)
    assert m1["beds"][0]["track"] == m2["beds"][0]["track"]


def test_decide_music_base_gain_clamped_to_max(tmp_path):
    """Garde-fou contrainte 1 : base_gain ne peut JAMAIS dépasser max_base_gain."""
    (tmp_path / "Luxury").mkdir()
    _mk_track(str(tmp_path / "Luxury" / "a.mp3"))
    _mk_track(str(tmp_path / "Luxury" / "b.mp3"))
    _mk_track(str(tmp_path / "Luxury" / "c.mp3"))
    m = _decide_music([], [], 0, [(0.0, 10.0)], 10.0,
                      music_root=str(tmp_path), rng_seed=0)
    # max_base_gain = -16 -> base ne peut pas être au-dessus de -16 (vers 0 = plus fort)
    assert m["beds"][0]["base_gain_dB"] <= -16.0


# ============== _compute_quality_score ==============

def test_quality_score_full():
    dbg = {"voice_dominance_dB": 7.0, "duck_depth_dB_effective": -12.0,
           "duck_depth_dB_requested": -12.0,
           "gaps": [{"start": 10.0, "end": 11.2}], "cta_detected": True,
           "lufs_final_target": -16.0, "lufs_final_actual": -15.5,
           "fallback_used": False}
    assert _compute_quality_score(dbg) == 1.0


def test_quality_score_zero_on_all_failures():
    dbg = {"voice_dominance_dB": 5.0, "duck_depth_dB_effective": -8.0,
           "duck_depth_dB_requested": -12.0,
           "gaps": [], "cta_detected": True,
           "lufs_final_target": -16.0, "lufs_final_actual": -19.0,
           "fallback_used": True}
    assert _compute_quality_score(dbg) == 0.0


def test_quality_score_cta_absent_is_neutralized():
    """Pas de CTA -> ce critère compte automatiquement comme vert."""
    dbg = {"voice_dominance_dB": 7.0, "duck_depth_dB_effective": -12.0,
           "duck_depth_dB_requested": -12.0,
           "gaps": [], "cta_detected": False,
           "lufs_final_target": -16.0, "lufs_final_actual": -16.0,
           "fallback_used": False}
    assert _compute_quality_score(dbg) == 1.0


def test_quality_score_partial_3_of_5():
    """3 critères verts sur 5 -> 0.6."""
    dbg = {"voice_dominance_dB": 7.0, "duck_depth_dB_effective": -12.0,
           "duck_depth_dB_requested": -12.0,
           "gaps": [], "cta_detected": True,    # gap manquant alors CTA détecté -> rouge
           "lufs_final_target": -16.0, "lufs_final_actual": -19.0,  # rouge (écart >1.5)
           "fallback_used": False}
    # dominance OK + ducking OK + fallback OK = 0.6 (CTA red + LUFS red)
    assert _compute_quality_score(dbg) == 0.6


# ============== build_plan: music dans le plan global ==============

def test_build_plan_includes_music_key():
    tokens = [{"disp": "Rolex", "start": 1.0, "end": 1.4, "sent": 0}]
    plan = build_plan([_kw("Rolex")], tokens, 1, [(0.0, 5.0)], 5.0)
    assert "music" in plan   # même si None (banque non configurée en test)


def test_build_plan_music_is_none_when_no_library():
    """Sans MUSIC_DIR rempli, le Director laisse music=None (no-op aval)."""
    tokens = [{"disp": "Rolex", "start": 1.0, "end": 1.4, "sent": 0}]
    plan = build_plan([_kw("Rolex")], tokens, 1, [(0.0, 5.0)], 5.0)
    # MUSIC_DIR par défaut est <project>/MUSIC qui n'a probablement pas Luxury/Hype rempli
    # en environnement de test -> music = None
    assert plan["music"] is None or plan["music"]["beds"]  # tolérant si banque réelle existe
