import pytest
pytestmark = pytest.mark.skip(reason="V2 en pause — rollback V1 demande proprietaire 2026-07-03")
import importlib.util
import json
import os
import re

BANK_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "stories_v2.json")
GEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "generate_stories_v2.py")
BANK = json.load(open(BANK_PATH, encoding="utf-8"))

_spec = importlib.util.spec_from_file_location("gen_stories_v2", GEN_PATH)
gs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gs)

FORBIDDEN = re.compile(r"[❀🚨🌴⬇️📩✅❌🔥💡]|INTÉRESSÉ|DM « MONTRE|Promo|barr", re.IGNORECASE)


def _all_frames():
    out = []
    for hid, hl in BANK["highlights"].items():
        out += [(hid, f) for f in hl["frames"]]
    for fid, fam in BANK["daily_families"].items():
        out += [(fid, f) for f in fam["frames"]]
    return out


def test_models_highlight_structure():
    frames = BANK["highlights"]["models"]["frames"]
    assert len(frames) == 6
    model_frames = [f for f in frames if f["template_id"] == "hero_model"]
    assert len(model_frames) == 5
    assert [f["model_id"] for f in model_frames] == \
        ["aurora", "nocturne", "braise", "eclipse", "meridien"]      # 5 écrans distincts
    assert all(f["cta_type"] == "none" for f in model_frames)        # aucun CTA intermédiaire
    last = frames[-1]
    assert last["cta_type"] == "dm_choix" and "tienne" in last["on_screen_text"]
    # pas d'écran d'intro générique
    assert all((f.get("on_screen_text") or "") != "La collection" for f in frames)


def test_no_highlight_frame_has_two_models():
    for hid, hl in BANK["highlights"].items():
        for f in hl["frames"]:
            assert f.get("model_id") is None or isinstance(f["model_id"], str), \
                (hid, f["frame_id"])


def test_choose_sequence_texts():
    txts = [f["on_screen_text"] for f in BANK["highlights"]["choose"]["frames"]]
    assert txts == ["Pas sûr du modèle qui te va ?",
                    "Ton poignet · tes couleurs · ton usage",
                    "Je t'aide à trouver celle qui te va.",
                    "Envoie « CHOIX » en DM"]
    assert all("gratuit" not in (t or "").lower() for t in txts)  # non confirmé


def test_reviews_fully_blocked_with_briefs():
    for f in BANK["highlights"]["reviews"]["frames"]:
        assert f["render_mode"] == "requires_real_asset"
        assert f["claim_status"] == "blocked"
        assert f.get("on_screen_text") is None       # jamais de faux template rempli
        assert f.get("internal_brief")


def test_quality_macro_is_not_a_control_claim():
    frames = {f["frame_id"]: f for f in BANK["highlights"]["quality"]["frames"]}
    auto = [f for f in frames.values() if f["render_mode"] == "automatic"]
    assert len(auto) == 1 and auto[0]["frame_id"] == "qua_02"
    low = (auto[0]["on_screen_text"] or "").lower()
    for bad in ("vérifi", "contrôl", "passe entre mes mains", "prête pour"):
        assert bad not in low
    for fid in ("qua_01", "qua_03", "qua_04"):
        assert frames[fid]["render_mode"] == "requires_real_asset"


def test_shipping_blocked_without_facts():
    facts = gs.sv.load_facts()
    entries = gs.process_frames(BANK["highlights"]["shipping"]["frames"], "shipping",
                                ".", dry_run=True, facts=facts)
    assert all(e["render_status"] == "blocked_unverified_claim" for e in entries)


def test_no_unverified_claim_rendered_and_availability_gated():
    facts = gs.sv.load_facts()
    fam = BANK["daily_families"]["availability"]["frames"]
    entries = gs.process_frames(fam, "availability", ".", dry_run=True, facts=facts,
                                model="aurora")
    assert entries[0]["render_status"] == "blocked_unverified_claim"  # pas de stock vérifié


def test_poll_sticker_marked_manual():
    f = BANK["daily_families"]["help_me_choose"]["frames"][0]
    assert f["manual_instagram_action"] == "poll_sticker"


def test_no_emoji_old_cta_or_floral_symbol():
    for seq, f in _all_frames():
        for k in ("on_screen_text", "subtext", "cta_text", "internal_brief"):
            v = f.get(k) or ""
            assert not FORBIDDEN.search(v), (seq, f["frame_id"], k, v)
    # le renderer lui-même refuse les textes interdits
    assert not gs.sv.check_frame_text({"frame_id": "x", "on_screen_text": "Promo ❌",
                                       "subtext": "", "cta_text": ""})


def test_dry_run_continues_despite_blocked():
    facts = gs.sv.load_facts()
    entries = []
    for hid, hl in BANK["highlights"].items():
        entries += gs.process_frames(hl["frames"], hid, ".", dry_run=True, facts=facts)
    counts = {}
    for e in entries:
        counts[e["render_status"]] = counts.get(e["render_status"], 0) + 1
    assert counts.get("dry_run_ok", 0) >= 12          # les vérifiées passent
    assert counts.get("blocked_missing_asset", 0) >= 7
    assert counts.get("blocked_unverified_claim", 0) >= 6
    assert len(entries) == sum(counts.values())        # rien n'a interrompu la boucle


def test_no_publish_function_anywhere():
    for path in (GEN_PATH,
                 os.path.join(os.path.dirname(__file__), "..", "posts", "stories_v2.py")):
        src = open(path, encoding="utf-8").read().lower()
        assert "uploadpost" not in src and "upload-post.com" not in src


def test_render_traceability_enforced():
    # un rendu qui utilise une image SANS tracer sa source doit échouer
    fr = {"frame_id": "x", "template_id": "hero_model", "model_id": "aurora",
          "asset_id": None, "claim_status": "verified",
          "manual_instagram_action": None}
    import pytest
    with pytest.raises(RuntimeError):
        gs._entry(fr, "seq", "rendered", out_path="x.png", resolved=None)
    e = gs._entry(fr, "seq", "rendered", out_path="x.png",
                  resolved={"resolved_asset_id": "a", "resolved_asset_path": "/p/a.jpg",
                            "source_hash": "h", "source_width": 10, "source_height": 10})
    assert e["resolved_asset_path"] == "/p/a.jpg" and e["source_hash"] == "h"
    assert e["requested_asset_id"] is None            # demandé ≠ résolu, distingués


def test_brand_asset_fields_always_present():
    fr = {"frame_id": "x", "template_id": "minimal_text", "model_id": None,
          "asset_id": None, "claim_status": "verified", "manual_instagram_action": None}
    e = gs._entry(fr, "seq", "dry_run_ok")
    assert "brand_asset_id" in e and "brand_asset_path" in e and "brand_asset_hash" in e
    # si l'avatar master est déposé, il DOIT être identifié fc_avatar_v1
    if os.path.isfile(gs.sv.AVATAR_PATH):
        assert e["brand_asset_id"] == "fc_avatar_v1" and e["brand_asset_hash"]


def test_asset_info_traces_hash_and_dims(tmp_path):
    from PIL import Image
    p = tmp_path / "src.png"
    Image.new("RGB", (321, 123), "#333333").save(p)
    info = gs._asset_info(str(p))
    assert info["source_width"] == 321 and info["source_height"] == 123
    assert len(info["source_hash"]) == 16 and info["resolved_asset_path"].endswith("src.png")


def test_real_render_dimensions_and_not_blank(tmp_path):
    from PIL import Image
    fr = {"frame_id": "t1", "template_id": "minimal_text",
          "on_screen_text": "Laquelle est la tienne ?", "subtext": "",
          "cta_type": "dm_choix", "cta_text": "Écris « CHOIX » en DM",
          "model_id": None, "asset_id": None}
    out = str(tmp_path / "t1.png")
    gs.sv.render_frame(fr, out)
    im = Image.open(out)
    assert im.size == (1080, 1920)                        # dimensions exactes
    lo, hi = im.convert("L").getextrema()
    assert hi - lo > 60                                   # ni vide ni uni


def test_model_screens_share_template_and_margins():
    frames = [f for f in BANK["highlights"]["models"]["frames"]
              if f["template_id"] == "hero_model"]
    assert len({f["template_id"] for f in frames}) == 1   # même template = mêmes marges
    assert all((f.get("cta_text") or "") == "" for f in frames)  # un seul bloc CTA (fin de séquence)


def test_covers_60_files_legible():
    from PIL import Image
    d = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "highlight_covers")
    for n in ("models", "choose", "reviews", "quality", "shipping", "faq"):
        p = os.path.join(d, f"cover_{n}_60.png")
        assert os.path.isfile(p), p
        im = Image.open(p)
        assert im.size == (60, 60)
        lo, hi = im.convert("L").getextrema()
        assert hi - lo > 80, f"cover {n} illisible/vide à 60px"


def test_no_typographic_fallback_allowed(monkeypatch):
    # master absent -> le rendu DOIT échouer (MissingBrandAsset), jamais de texte FC
    monkeypatch.setattr(gs.sv, "MONOGRAM_PATH", "Z:/nulle/part.png")
    import pytest
    fr = {"frame_id": "x", "template_id": "minimal_text", "on_screen_text": "Test",
          "subtext": "", "cta_text": "", "model_id": None, "asset_id": None}
    with pytest.raises(gs.sv.MissingBrandAsset):
        gs.sv.render_frame(fr, "unused.png")


def test_rendered_entry_requires_brand_asset(monkeypatch):
    import pytest
    fr = {"frame_id": "x", "template_id": "minimal_text", "model_id": None,
          "asset_id": None, "claim_status": "verified", "manual_instagram_action": None}
    monkeypatch.setattr(gs.sv, "MONOGRAM_PATH", "Z:/nulle/part.png")
    with pytest.raises(RuntimeError):
        gs._entry(fr, "seq", "rendered", out_path="x.png")


def test_preferred_assets_used():
    # la photo Éclipse ne doit PLUS être la boîte orange (silver_01) mais silver_02
    p = gs.sv.photo_for_model("eclipse")
    assert p and p.endswith("silver_02.jpeg")
    assert gs.sv.photo_for_model("meridien").endswith("gmt_02.jpeg")
    assert gs.sv.photo_for_model("aurora").endswith("or_rose_04.jpeg")


def test_presentation_mode_on_photo_frames():
    for hid, hl in BANK["highlights"].items():
        for f in hl["frames"]:
            if f["template_id"] in ("hero_model", "detail_macro"):
                assert f.get("presentation_mode") == "nocturne_frame", (hid, f["frame_id"])


def test_no_collision_monogram_cta_photo_zones(tmp_path):
    """Collision réelle mesurée dans le navigateur : monogramme vs CTA vs cadre
    photo vs zones de sécurité (haut 220 / bas 280)."""
    from playwright.sync_api import sync_playwright
    fr = {"frame_id": "c1", "template_id": "hero_model",
          "presentation_mode": "nocturne_frame", "model_id": "aurora",
          "on_screen_text": "FC Aurora", "subtext": "La lumière chaude",
          "cta_type": "profile_visit", "cta_text": "Collection sur le profil",
          "asset_id": None}
    photo = gs.sv.photo_for_model("aurora")
    html = gs.sv.TEMPLATES["hero_model_framed"](fr, photo)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_context(viewport={"width": 1080, "height": 1920}).new_page()
        page.set_content(html)
        page.wait_for_timeout(250)
        def box(sel):
            return page.evaluate(
                "s => {const e=document.querySelector(s); if(!e) return null;"
                "const r=e.getBoundingClientRect();"
                "return {x:r.x,y:r.y,r:r.x+r.width,b:r.y+r.height};}", sel)
        mono = box(".monoimg"); cta = box(".cta"); img = box("img:not(.monoimg)")
        b.close()
    assert mono and cta
    def intersects(a, c):
        return not (a["r"] <= c["x"] or c["r"] <= a["x"] or a["b"] <= c["y"] or c["b"] <= a["y"])
    # NB : .cta est un bloc pleine largeur -> on vérifie la séparation VERTICALE
    assert cta["b"] <= mono["y"], "CTA doit être au-dessus du monogramme"
    assert not intersects(mono, img), "monogramme sur la photo"
    assert mono["b"] <= 1920 - 280 and cta["b"] <= 1920 - 280   # zone basse
    assert cta["y"] >= 220 and mono["y"] >= 220                  # zone haute
    assert img["b"] <= cta["y"], "photo doit finir au-dessus du CTA"


def test_covers_pack_definition():
    assert set(gs.COVERS) == {"models", "choose", "reviews", "quality", "shipping", "faq"}
    for name, spec in gs.COVERS.items():
        svg = gs._SVG_FRAME.format(glyph=spec["glyph"], amber=spec["amber"])
        assert "<text" not in svg                      # aucun texte dans l'icône
        assert 'stroke-width="26"' in svg              # trait épais identique
        assert "#070707" in svg and "#C99645" in svg   # fond + reflet ambre
