import pytest
pytestmark = pytest.mark.skip(reason="V2 en pause — rollback V1 demande proprietaire 2026-07-03")
"""Tests de rendu réel des layouts V2 sequence_2 / sequence_3. Fixtures légères :
un clip couleur minuscule (0.5s) au lieu de la vraie banque -> rapide."""
import os
import pytest
from backend import ffmpeg
from backend.config import SILENT
from backend.silent.recipe import VideoRecipe
from backend.silent import render


def _tiny_clip(path, color="blue"):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", f"color=c={color}:s=240x360:d=0.5:r=30",
                "-pix_fmt", "yuv420p", os.path.abspath(path)])
    assert os.path.exists(path)
    return os.path.abspath(path)


def _duration(path):
    r = ffmpeg.run([ffmpeg.FFPROBE, "-v", "error", "-show_entries",
                    "format=duration", "-of", "csv=p=0", path])
    return float(r.stdout.strip())


def _recipe(mechanic, layout, assets, cta_type):
    return VideoRecipe(
        mechanic=mechanic, layout=layout, hook="Laquelle te ressemble ?",
        content_angle="x", assets=tuple(assets), duration=SILENT["min_duration"],
        font=SILENT["fonts"][0], accent=SILENT["accents"][0], text_anim="fade",
        seed=1, cta_type=cta_type)


def test_sequence_2_renders_valid_mp4(tmp_path):
    clip = _tiny_clip(tmp_path / "a.mp4")
    out = str(tmp_path / "seq2.mp4")
    render.render_recipe(_recipe("projection", "sequence_2", [clip, clip], "save_share"), out)
    assert os.path.exists(out) and os.path.getsize(out) > 0
    assert abs(_duration(out) - SILENT["min_duration"]) < 0.6


def test_sequence_3_renders_valid_mp4(tmp_path):
    clip = _tiny_clip(tmp_path / "a.mp4")
    out = str(tmp_path / "seq3.mp4")
    render.render_recipe(_recipe("test", "sequence_3", [clip, clip, clip], "profile_visit"), out)
    assert os.path.exists(out) and os.path.getsize(out) > 0
    assert abs(_duration(out) - SILENT["min_duration"]) < 0.6
