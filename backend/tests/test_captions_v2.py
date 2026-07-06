import pytest
pytestmark = pytest.mark.skip(reason="V2 en pause — rollback V1 demande proprietaire 2026-07-03")
import json
import os
import re
from backend.silent import captions_v2, cta_v2, canon

BATCH = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "test_batch_v2.json")
CONCEPTS = json.load(open(BATCH, encoding="utf-8"))["concepts"]
RENDERABLE = [c for c in CONCEPTS if not captions_v2.is_blocked(c)]
BLOCKED = [c for c in CONCEPTS if captions_v2.is_blocked(c)]
_ALLOWED = {h.lower() for h in captions_v2.ALLOWED_HASHTAGS}


def _cap(c):
    return captions_v2.build(c, None)


def test_split_counts():
    assert len(RENDERABLE) == 22 and len(BLOCKED) == 2


def test_blocked_return_none():
    for c in BLOCKED:
        assert captions_v2.build(c, None) is None
    assert {c["concept_id"] for c in BLOCKED} == {"preuve_01", "preuve_03"}


def test_all_renderable_get_a_caption_and_pass_guardrails():
    for c in RENDERABLE:
        cap = _cap(c)
        assert cap and cap.strip(), c["concept_id"]
        ok, why = captions_v2.validate(cap, c)
        assert ok, f"{c['concept_id']}: {why}"


def test_no_canon_term_and_max_3_whitelist_hashtags():
    for c in RENDERABLE:
        cap = _cap(c)
        assert canon.is_clean(cap), c["concept_id"]
        tags = re.findall(r"#\w+", cap)
        assert len(tags) <= 3 and all(t.lower() in _ALLOWED for t in tags), (c["concept_id"], tags)
        low = cap.lower()
        assert "#seikomod" not in low and "#seiko" not in low and "#rolex" not in low


def test_no_save_share_type_anywhere():
    assert "save_share" not in cta_v2.VALID
    for c in CONCEPTS:
        assert c["cta_type"] != "save_share"
    # projection utilise bien save ET share sur des concepts différents
    proj = {c["cta_type"] for c in CONCEPTS if c["family_id"] == "projection"}
    assert "save" in proj and "share" in proj


def test_dm_keyword_only_in_dm_families():
    for c in RENDERABLE:
        cap = _cap(c)
        kw = ("«" in cap) or bool(re.search(r"\bdm\b", cap.lower()))
        assert kw == cta_v2.uses_dm(c["cta_type"]), c["concept_id"]


def test_captions_are_concept_specific():
    # aucune valeur éditoriale interchangeable : les captions rendues sont distinctes
    caps = [_cap(c) for c in RENDERABLE]
    assert len(set(caps)) == len(caps)


def test_conseil_gives_concrete_criterion():
    for c in RENDERABLE:
        if c["family_id"] == "conseil":
            cap = _cap(c).lower()
            # le critère concret vient du bloc valeur (boîtier, cadran, semaine, usage…)
            assert any(k in cap for k in ("boîtier", "cadran", "semaine", "usage", "porter"))
            assert "«" in _cap(c)  # DM CHOIX personnalisé présent


def test_hooks_not_copied_and_openings_varied():
    for c in RENDERABLE:
        assert c["hook"].strip().lower() not in _cap(c).lower(), c["concept_id"]
    firsts = {_cap(c).split("\n")[0].strip() for c in RENDERABLE}
    assert len(firsts) >= 8


def test_modes_length_and_no_stats_no_sigma():
    for c in RENDERABLE:
        cap = _cap(c)
        mode = captions_v2.MODE_BY_FAMILY[c["family_id"]]
        assert len(cap) <= (240 if mode == "premium_short" else 360), c["concept_id"]
        assert not re.search(r"\d+\s*%", cap)
        for bad in captions_v2.SIGMA_BLACKLIST:
            assert bad not in cap.lower(), (c["concept_id"], bad)


def test_preuve_renderable_never_fabricates():
    for c in RENDERABLE:
        if c["family_id"] == "preuve":
            low = _cap(c).lower()
            for bad in ("avis client", "témoignage", "garantie", "jours", "remboursé", "%"):
                assert bad not in low, (c["concept_id"], bad)


def test_removed_formulations_absent():
    banned_copy = ["pose un homme", "s'oublie à ton poignet",
                   "parle pour toi quand tu entres", "commentaire 👇",
                   "qu'on remarque sans que", "la méridien", "la nocturne est",
                   "#horlogerie", "dispo —"]
    for c in RENDERABLE:
        low = _cap(c).lower()
        for bad in banned_copy:
            assert bad.lower() not in low, (c["concept_id"], bad)


def test_fallback_without_gemini(monkeypatch):
    monkeypatch.setattr(captions_v2.caption_seo, "_gemini_key", lambda: None)
    cap = captions_v2.build(RENDERABLE[0], ["FC Aurora"])
    assert cap and captions_v2.validate(cap, RENDERABLE[0])[0]
