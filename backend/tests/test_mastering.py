"""Mastering LUFS V1 — tests TDD.

Critères validation reviewer :
- LUFS final ∈ [target-1.5 ; target+1.5]
- Pas de clipping (true peak ≤ -1 dBTP)
- Dominance voix toujours > 6 dB (préservée)
- No-op strict si mastering désactivé
- Coût < +10%
"""
import os
import hashlib
import subprocess

import pytest

from backend import ffmpeg, service
from backend import config as cfg
from backend.pipeline import audio_meta
from backend.pipeline.montage import render


def _mini_ass(path):
    open(path, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
        "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,80,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,"
        "&H00000000&,1,0,0,0,100,100,0,0,1,4,0,5,80,80,80,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,TEST\n")


def _pcm_hash(path):
    """SHA-256 du PCM mono 16k pour détecter toute différence audio."""
    p = subprocess.run([ffmpeg.FFMPEG, "-v", "quiet", "-i", path,
                        "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                       capture_output=True)
    return hashlib.sha256(p.stdout).hexdigest()


def _true_peak_dbtp(path):
    """True peak du fichier via loudnorm (linear=true mode pass1)."""
    r = ffmpeg.run([ffmpeg.FFMPEG, "-i", path, "-af",
                    "loudnorm=print_format=summary", "-f", "null", "-"])
    import re
    m = re.search(r"Input True Peak:\s*(-?[0-9.]+)\s*dBTP", r.stderr)
    try:
        return float(m.group(1)) if m else 0.0
    except (ValueError, AttributeError):
        return 0.0


# ---------- 1. No-op strict si master=None ----------

def test_render_master_none_is_strict_noop(sample_audio, tmp_path):
    """master_lufs=None -> empreinte audio PCM IDENTIQUE au rendu sans mastering."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    out_a = str(tmp_path / "no_master.mp4")
    out_b = str(tmp_path / "master_none.mp4")
    render(sample_audio, ass, [(0.0, dur)], out_a, plan=None, seed=42)
    render(sample_audio, ass, [(0.0, dur)], out_b, plan=None, seed=42,
           master_lufs=None)
    assert _pcm_hash(out_a) == _pcm_hash(out_b), "PCM doit être strictement identique"


# ---------- 2. Mastering actif amène le LUFS dans la fenêtre ----------

def test_render_mastering_brings_lufs_within_tolerance(sample_audio, tmp_path):
    """Voix faible (~ -24 LUFS) doit sortir à -16 LUFS ±1.5 après mastering."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    out = str(tmp_path / "mastered.mp4")
    render(sample_audio, ass, [(0.0, dur)], out, plan=None, seed=42,
           master_lufs=-16.0)
    lufs = audio_meta.lufs_of(out)
    assert -17.5 <= lufs <= -14.5, f"LUFS hors fenêtre [-17.5;-14.5] : {lufs}"


# ---------- 3. True peak respecté (pas de clipping) ----------

def test_render_mastering_respects_true_peak(sample_audio, tmp_path):
    """Pas de clipping : true peak ≤ -1 dBTP après mastering."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    out = str(tmp_path / "mastered.mp4")
    render(sample_audio, ass, [(0.0, dur)], out, plan=None, seed=42,
           master_lufs=-16.0)
    tp = _true_peak_dbtp(out)
    assert tp <= -1.0, f"true peak trop haut: {tp} dBTP (attendu ≤ -1)"


# ---------- 4. service.make_video : mastering activé par défaut + debug ----------

def test_make_video_mastering_default_enriches_debug(monkeypatch, sample_audio, tmp_path):
    """Avec banque musique : debug contient pre/post_master + mastering_quality_score."""
    lux = tmp_path / "MUSIC" / "Luxury"; lux.mkdir(parents=True)
    for i, vol in enumerate(("-10dB", "-12dB", "-8dB")):
        ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=60",
                    "-af", f"volume={vol}", str(lux / f"t{i}.mp3")])
    monkeypatch.setattr(cfg, "MUSIC_DIR", str(tmp_path / "MUSIC"))

    out = str(tmp_path / "out.mp4")
    service.make_video(sample_audio,
                       "Cette Rolex est incroyable. Écris ROLEX en commentaire.",
                       out, style="karaoke_yellow")
    dbg = service._LAST_MUSIC_DEBUG
    assert dbg is not None
    # Debug enrichi
    assert "lufs_pre_master" in dbg
    assert "lufs_post_master" in dbg
    assert "mastering_applied" in dbg
    assert "mastering_quality_score" in dbg
    # Mastering appliqué + score
    assert dbg["mastering_applied"] is True
    assert dbg["lufs_post_master"] is not None
    assert -17.5 <= dbg["lufs_post_master"] <= -14.5
    # Score dédié : 1.0 attendu
    assert dbg["mastering_quality_score"] == 1.0


# ---------- 5. Garde-fou : dominance préservée après mastering ----------

def test_mastering_preserves_voice_dominance(monkeypatch, sample_audio, tmp_path):
    """Le mastering ne doit pas détruire la dominance voix (±2 dB max)."""
    lux = tmp_path / "MUSIC" / "Luxury"; lux.mkdir(parents=True)
    for i, vol in enumerate(("-10dB", "-12dB", "-8dB")):
        ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=60",
                    "-af", f"volume={vol}", str(lux / f"t{i}.mp3")])
    monkeypatch.setattr(cfg, "MUSIC_DIR", str(tmp_path / "MUSIC"))

    out = str(tmp_path / "out.mp4")
    service.make_video(sample_audio,
                       "Cette Rolex est incroyable. Écris ROLEX en commentaire.",
                       out, style="karaoke_yellow")
    dbg = service._LAST_MUSIC_DEBUG
    # Le delta dominance doit rester sous la tolérance config
    assert "voice_dominance_dB" in dbg
    assert dbg["voice_dominance_dB"] > 6.0, (
        f"dominance cassée par mastering : {dbg['voice_dominance_dB']}")


# ---------- 6. Quality score : règle 3 paliers ----------

def test_mastering_quality_score_within_tolerance():
    from backend.pipeline.director import _compute_mastering_quality_score
    # ±1.5 -> 1.0
    assert _compute_mastering_quality_score(-16.0, -16.0) == 1.0
    assert _compute_mastering_quality_score(-16.0, -17.5) == 1.0
    assert _compute_mastering_quality_score(-16.0, -14.5) == 1.0


def test_mastering_quality_score_warn_band():
    from backend.pipeline.director import _compute_mastering_quality_score
    # ±3 -> 0.5
    assert _compute_mastering_quality_score(-16.0, -18.5) == 0.5
    assert _compute_mastering_quality_score(-16.0, -13.5) == 0.5


def test_mastering_quality_score_failure():
    from backend.pipeline.director import _compute_mastering_quality_score
    # > ±3 -> 0.0
    assert _compute_mastering_quality_score(-16.0, -20.0) == 0.0
    assert _compute_mastering_quality_score(-16.0, -10.0) == 0.0


def test_mastering_quality_score_handles_none():
    """Si pas de mesure post (mastering désactivé) -> score None ou 0 logique."""
    from backend.pipeline.director import _compute_mastering_quality_score
    assert _compute_mastering_quality_score(-16.0, None) is None
