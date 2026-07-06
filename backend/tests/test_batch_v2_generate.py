import pytest
pytestmark = pytest.mark.skip(reason="V2 en pause — rollback V1 demande proprietaire 2026-07-03")
import importlib.util
import os
from backend import ffmpeg
from backend.config import FAMILIES_V2
from backend.silent import cta_v2

_GB = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "generate_batch_v2.py")
_spec = importlib.util.spec_from_file_location("gen_batch_v2", _GB)
gb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gb)


def _tiny_clip(path):
    ffmpeg.run([ffmpeg.FFMPEG, "-y", "-f", "lavfi",
                "-i", "color=c=teal:s=240x360:d=0.5:r=30",
                "-pix_fmt", "yuv420p", os.path.abspath(path)])
    return os.path.abspath(path)


def test_dry_run_validates_all_24(tmp_path):
    man = gb.main(dry_run=True, out_dir=str(tmp_path))
    assert man["total"] == 24
    assert man["counts"].get("dry_run_ok") == 22
    assert man["counts"].get("blocked_missing_asset") == 2
    assert "invalid" not in man["counts"] and "error" not in man["counts"]
    assert os.path.exists(tmp_path / "manifest.json")


def test_blocked_preuve_are_the_two_real_asset_ones(tmp_path):
    man = gb.main(dry_run=True, out_dir=str(tmp_path))
    blocked = [e for e in man["concepts"] if e["render_status"] == "blocked_missing_asset"]
    assert {e["concept_id"] for e in blocked} == {"preuve_01", "preuve_03"}
    for e in blocked:
        assert e["caption"] is None                       # aucun texte publiable
        assert e["caption_status"] == "blocked_missing_asset"
        assert e["missing_material"]                       # brief de matière attendue
        assert not os.path.exists(tmp_path / (e["concept_id"] + ".caption.txt"))


def test_render_one_concept_with_fixture(tmp_path):
    clip = _tiny_clip(tmp_path / "c.mp4")
    man = gb.main(dry_run=False, out_dir=str(tmp_path), only=["miroir_01"],
                  clip_resolver=lambda mid: clip)
    e = man["concepts"][0]
    assert e["render_status"] == "rendered", e
    assert os.path.exists(e["output_path"]) and os.path.getsize(e["output_path"]) > 0
    assert os.path.exists(e["caption_path"])


def test_missing_preuve_does_not_break_batch(tmp_path):
    clip = _tiny_clip(tmp_path / "c.mp4")
    # rend un concept rendable ET un concept Preuve bloqué : le batch continue.
    man = gb.main(dry_run=False, out_dir=str(tmp_path),
                  only=["miroir_01", "preuve_01"], clip_resolver=lambda mid: clip)
    st = {e["concept_id"]: e["render_status"] for e in man["concepts"]}
    assert st["miroir_01"] == "rendered"
    assert st["preuve_01"] == "blocked_missing_asset"


def test_cta_per_family_no_choix_leak():
    # Garde-fou : le mot-clé DM « CHOIX » (guillemets ou "DM") n'apparaît QUE dans
    # les familles DM. Le mot français « choix » (choice) reste autorisé ailleurs.
    for fam, spec in FAMILIES_V2.items():
        cap, scr = cta_v2.caption(spec["cta_type"]), cta_v2.screen(spec["cta_type"])
        keyword = ("«" in cap) or ("DM" in cap.upper()) or ("«" in scr) or ("DM" in scr.upper())
        if cta_v2.uses_dm(spec["cta_type"]):
            assert keyword, fam
        else:
            assert not keyword, fam
