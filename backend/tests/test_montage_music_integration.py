"""T7 — montage.render exécute le plan musique du Director."""
import os

from backend import ffmpeg
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


def _mk_track(path, dur=60, freq=440, vol="-10dB"):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", f"sine=frequency={freq}:duration={dur}",
                "-af", f"volume={vol}", path])


def _audio_duration(path):
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "a:0",
                    "-show_entries", "stream=duration", "-of", "csv=p=0", path])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _bed(track, dur, gaps=None):
    return {
        "track": track, "trim_start": 0.0, "start": 0.0, "duration": dur,
        "base_gain_dB": -22.0, "fade_in_ms": 800, "fade_out_ms": 1200,
        "duck": {"mode": "sidechain", "ratio": 6.0, "threshold_dB": -28,
                 "attack_ms": 8, "release_ms": 280, "depth_dB": -12.0,
                 "side": "voice"},
        "gaps": gaps or [],
    }


def test_render_with_music_produces_valid_video(sample_audio, tmp_path):
    """Rendu réel avec un plan['music'] complet : la vidéo sort, durée OK."""
    track = str(tmp_path / "music.mp3")
    _mk_track(track, dur=60)
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)

    plan_music = {
        "beds": [_bed(track, dur=dur)],
        "accents": [],
        "mix": {"target_lufs": -16.0, "voice_priority": True},
        "debug": {},
    }
    out = str(tmp_path / "with_music.mp4")
    render(sample_audio, ass, [(0.0, dur)], out,
           plan={"music": plan_music}, seed=42)

    assert os.path.exists(out)
    # Durée audio doit rester très proche de la voix originale (pas de drift)
    d = _audio_duration(out)
    assert abs(d - dur) < 0.20, f"audio drift with music: {d} vs {dur}"


def test_render_with_music_and_gap_produces_valid_video(sample_audio, tmp_path):
    """Test avec gap pré-CTA actif."""
    track = str(tmp_path / "music.mp3"); _mk_track(track, dur=60)
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)

    # Gap au milieu de la vidéo
    gap_start = dur * 0.6
    gap_end = gap_start + 1.0
    plan_music = {
        "beds": [_bed(track, dur=dur, gaps=[
            {"start": gap_start, "end": gap_end,
             "fade_out_ms": 250, "fade_in_ms": 200}
        ])],
        "accents": [],
        "mix": {"target_lufs": -16.0, "voice_priority": True},
        "debug": {},
    }
    out = str(tmp_path / "with_gap.mp4")
    render(sample_audio, ass, [(0.0, dur)], out,
           plan={"music": plan_music}, seed=42)

    assert os.path.exists(out)
    assert abs(_audio_duration(out) - dur) < 0.20


def test_render_audible_difference_with_vs_without_music(sample_audio, tmp_path):
    """Sanity : avec musique != sans musique (RMS différent attendu)."""
    track = str(tmp_path / "music.mp3"); _mk_track(track, dur=60, vol="-3dB")
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)

    out_silent = str(tmp_path / "silent.mp4")
    out_music = str(tmp_path / "music.mp4")
    render(sample_audio, ass, [(0.0, dur)], out_silent, plan=None, seed=42)
    plan_music = {
        "beds": [_bed(track, dur=dur)],
        "accents": [], "mix": {"target_lufs": -16.0}, "debug": {},
    }
    render(sample_audio, ass, [(0.0, dur)], out_music,
           plan={"music": plan_music}, seed=42)

    # Empreinte PCM doit DIFFÉRER (la musique a été ajoutée au mix)
    import hashlib
    import subprocess

    def _hash(p):
        r = subprocess.run([ffmpeg.FFMPEG, "-v", "quiet", "-i", p,
                            "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                           capture_output=True)
        return hashlib.sha256(r.stdout).hexdigest()

    assert _hash(out_silent) != _hash(out_music), \
        "audio fingerprint should differ when music is present"
