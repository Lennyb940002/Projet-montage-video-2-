"""T8 — auto-fix non bloquant + remplissage debug + music_quality_score.

Règle produit absolue : make_video DOIT toujours retourner une vidéo.
Si la voix n'est pas assez dominante, on auto-fix une fois ; si ça ne suffit
pas, on logge un warning et on garde la vidéo.
"""
import pytest

from backend import service


# ---------- _music_dominance_autofix (unité) ----------

def test_autofix_not_triggered_when_dominance_ok(monkeypatch):
    """Dominance déjà >= seuil : pas d'auto-fix, debug propre."""
    from backend.pipeline import audio_meta
    monkeypatch.setattr(audio_meta, "measure_dominance", lambda *a, **kw: 9.0)
    debug = {"voice_dominance_dB": None, "auto_fix_applied": False,
             "warnings": [], "duck_depth_dB_effective": -12.0}
    calls = {"n": 0}

    def fake_render(new_gain):
        calls["n"] += 1
    service._music_dominance_autofix(
        debug, render_callable=fake_render, current_gain=-22.0,
        voice_path="v.wav", mix_path="m.mp4", voice_active=[(0, 1)],
    )
    assert calls["n"] == 0
    assert debug["voice_dominance_dB"] == 9.0
    assert debug["auto_fix_applied"] is False
    assert debug["warnings"] == []


def test_autofix_triggered_and_succeeds(monkeypatch):
    """Dominance < seuil au 1er rendu, OK après auto-fix : 1 re-render."""
    from backend.pipeline import audio_meta
    calls = {"meas": 0, "render": 0}

    def fake_meas(*a, **kw):
        calls["meas"] += 1
        return 3.0 if calls["meas"] == 1 else 8.0
    monkeypatch.setattr(audio_meta, "measure_dominance", fake_meas)
    debug = {"voice_dominance_dB": None, "auto_fix_applied": False,
             "warnings": [], "duck_depth_dB_effective": -12.0}
    service._music_dominance_autofix(
        debug, render_callable=lambda g: calls.__setitem__("render", calls["render"] + 1),
        current_gain=-22.0, voice_path="v.wav", mix_path="m.mp4",
        voice_active=[(0, 1)],
    )
    assert calls["render"] == 1
    assert debug["auto_fix_applied"] is True
    assert debug["voice_dominance_dB"] == 8.0
    assert any("auto-reduced" in w for w in debug["warnings"])


def test_autofix_keeps_warning_when_still_below_threshold(monkeypatch):
    """Dominance < seuil au 1er ET au 2e rendu : on garde la vidéo + warning."""
    from backend.pipeline import audio_meta
    monkeypatch.setattr(audio_meta, "measure_dominance", lambda *a, **kw: 3.0)
    debug = {"voice_dominance_dB": None, "auto_fix_applied": False,
             "warnings": [], "duck_depth_dB_effective": -12.0}
    ok, debug = service._music_dominance_autofix(
        debug, render_callable=lambda g: None, current_gain=-22.0,
        voice_path="v.wav", mix_path="m.mp4", voice_active=[(0, 1)],
    )
    assert ok is True  # JAMAIS bloquant
    assert debug["auto_fix_applied"] is True
    assert any("still below" in w for w in debug["warnings"])


def test_autofix_returns_ok_true_no_matter_what(monkeypatch):
    """Garantie produit : ok=True dans TOUS les cas (jamais d'exception)."""
    from backend.pipeline import audio_meta

    def crash(*a, **kw):
        raise RuntimeError("boom")
    # Le wrapper doit absorber les erreurs internes sans casser le rendu
    monkeypatch.setattr(audio_meta, "measure_dominance", crash)
    debug = {"voice_dominance_dB": None, "auto_fix_applied": False,
             "warnings": [], "duck_depth_dB_effective": -12.0}
    ok, debug = service._music_dominance_autofix(
        debug, render_callable=lambda g: None, current_gain=-22.0,
        voice_path="v.wav", mix_path="m.mp4", voice_active=[(0, 1)],
    )
    assert ok is True
    assert any("autofix internal error" in w.lower() for w in debug["warnings"])


# ---------- make_video : intégration end-to-end ----------

def test_make_video_no_library_still_produces_video(monkeypatch, sample_audio, tmp_path):
    """Pas de banque musique configurée -> vidéo produite quand même (no-op)."""
    out = str(tmp_path / "out.mp4")
    # Banque vide -> Director renvoie plan["music"]=None
    monkeypatch.setattr(service, "MUSIC_DIR_OVERRIDE", str(tmp_path / "nope"),
                        raising=False)
    res = service.make_video(sample_audio,
                             text="Voici une démonstration sans musique.",
                             out_path=out, style="karaoke_yellow")
    import os
    assert os.path.exists(res)


def test_make_video_with_music_fills_debug(monkeypatch, sample_audio, tmp_path):
    """Avec banque rempliée, le debug contient les mesures LUFS et le score."""
    from backend import ffmpeg
    # Préparer une mini-banque Luxury 3 tracks longs
    lux = tmp_path / "MUSIC" / "Luxury"
    lux.mkdir(parents=True)
    for i, vol in enumerate(("-12dB", "-14dB", "-10dB")):
        ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=60",
                    "-af", f"volume={vol}", str(lux / f"t{i}.mp3")])
    # Override MUSIC_DIR via monkeypatch
    import backend.config as cfg
    monkeypatch.setattr(cfg, "MUSIC_DIR", str(tmp_path / "MUSIC"))
    # Director utilise MUSIC_DIR par défaut quand music_root=None ;
    # on force aussi côté service (futur paramètre).
    monkeypatch.setattr(service, "MUSIC_DIR_OVERRIDE",
                        str(tmp_path / "MUSIC"), raising=False)

    out = str(tmp_path / "with_music.mp4")
    res = service.make_video(
        sample_audio,
        text="Cette Rolex est vraiment incroyable. Écris ROLEX en commentaire.",
        out_path=out, style="karaoke_yellow",
    )
    import os
    assert os.path.exists(res)
    # Le debug doit avoir été enrichi par service après le rendu
    dbg = service._LAST_MUSIC_DEBUG
    assert dbg is not None, "service doit exposer le dernier debug musique"
    assert dbg["lufs_voice"] is not None
    assert dbg["lufs_music_source"] is not None
    assert dbg["lufs_final_actual"] is not None
    assert dbg["voice_dominance_dB"] is not None
    assert dbg["music_quality_score"] is not None
    assert 0.0 <= dbg["music_quality_score"] <= 1.0
