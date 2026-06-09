"""Garde-fou strict avant T7 : `plan["music"]=None` doit produire un rendu
AUDIO STRICTEMENT ÉQUIVALENT à `plan=None` (= ancien pipeline sans musique).

3 dimensions vérifiées :
  1. Wiring : music_engine.build(None, ...) renvoie no-op pur.
  2. Durée : audio du rendu identique avec ou sans clé "music":None.
  3. Empreinte audio (hash PCM) : aucune différence binaire post-décodage.
"""
import hashlib
import os

from backend import ffmpeg
from backend.pipeline import music_engine
from backend.pipeline.montage import render


# ---------- helpers ----------

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


def _audio_duration(path):
    """Durée précise du flux audio (s)."""
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "quiet", "-select_streams", "a:0",
                    "-show_entries", "stream=duration", "-of", "csv=p=0", path])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _audio_pcm_hash(path):
    """Décode l'audio en PCM mono 16 kHz s16le puis hash SHA-256.
    Comparaison insensible au container/timestamp, sensible au signal."""
    r = ffmpeg.run([ffmpeg.FFMPEG, "-v", "quiet", "-i", path,
                    "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"])
    # ffmpeg.run renvoie stdout en TEXTE -> on doit re-passer en raw pour le hash.
    # Solution : capture via subprocess directe en mode binaire.
    import subprocess
    p = subprocess.run([ffmpeg.FFMPEG, "-v", "quiet", "-i", path,
                        "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                       capture_output=True)
    return hashlib.sha256(p.stdout).hexdigest()


def _audio_rms_dbfs(path):
    """RMS (dBFS) global du fichier."""
    import re
    r = ffmpeg.run([ffmpeg.FFMPEG, "-i", path, "-af", "astats", "-f", "null", "-"])
    matches = re.findall(r"RMS level dB:\s*(-?[0-9.]+)", r.stderr)
    return float(matches[-1]) if matches else -90.0


# ---------- Dimension 1 : wiring ----------

def test_music_engine_noop_returns_voice_label_unchanged():
    """Pré-requis logique de l'intégration T7."""
    out_none = music_engine.build(None, voice_label="vmix", base_input_idx=5)
    out_empty = music_engine.build({"beds": [], "accents": []}, "vmix", 5)
    for o in (out_none, out_empty):
        assert o["extra_inputs"] == []
        assert o["filter_str"] == ""
        assert o["out_label"] == "vmix"
        assert o["beds_processed"] == 0
        assert o["accents_processed"] == 0


# ---------- Dimension 2 : durée audio ----------

def test_render_duration_unchanged_with_music_none_key(sample_audio, tmp_path):
    """plan={'music':None} ne doit PAS changer la durée audio vs plan=None."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    out_a = str(tmp_path / "no_plan.mp4")
    out_b = str(tmp_path / "music_none.mp4")
    render(sample_audio, ass, [(0.0, dur)], out_a, plan=None, seed=42)
    render(sample_audio, ass, [(0.0, dur)], out_b, plan={"music": None}, seed=42)
    assert os.path.exists(out_a) and os.path.exists(out_b)
    d_a, d_b = _audio_duration(out_a), _audio_duration(out_b)
    assert abs(d_a - d_b) < 0.05, f"audio drift: {d_a} vs {d_b}"
    # marge de sécurité : pas non plus de désync audio vs voix source
    assert abs(d_a - dur) < 0.10


# ---------- Dimension 3 : empreinte audio identique ----------

def test_render_audio_fingerprint_unchanged_with_music_none(sample_audio, tmp_path):
    """plan={'music':None} -> audio PCM décodé IDENTIQUE à plan=None."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    out_a = str(tmp_path / "no_plan.mp4")
    out_b = str(tmp_path / "music_none.mp4")
    render(sample_audio, ass, [(0.0, dur)], out_a, plan=None, seed=42)
    render(sample_audio, ass, [(0.0, dur)], out_b, plan={"music": None}, seed=42)
    h_a, h_b = _audio_pcm_hash(out_a), _audio_pcm_hash(out_b)
    assert h_a == h_b, f"audio fingerprint differs: {h_a[:12]} != {h_b[:12]}"


# ---------- Bonus : sanity RMS ----------

def test_render_audio_rms_unchanged_with_music_none(sample_audio, tmp_path):
    """RMS global doit être identique (à 0.01 dB près) entre les deux rendus."""
    ass = str(tmp_path / "s.ass"); _mini_ass(ass)
    dur = ffmpeg.probe_duration(sample_audio)
    out_a = str(tmp_path / "no_plan.mp4")
    out_b = str(tmp_path / "music_none.mp4")
    render(sample_audio, ass, [(0.0, dur)], out_a, plan=None, seed=42)
    render(sample_audio, ass, [(0.0, dur)], out_b, plan={"music": None}, seed=42)
    rms_a, rms_b = _audio_rms_dbfs(out_a), _audio_rms_dbfs(out_b)
    assert abs(rms_a - rms_b) < 0.01, f"RMS drift: {rms_a:.3f} vs {rms_b:.3f}"
