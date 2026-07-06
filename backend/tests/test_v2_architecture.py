import pytest
pytestmark = pytest.mark.skip(reason="V2 en pause — rollback V1 demande proprietaire 2026-07-03")
import json
import os
from backend.config import SILENT, FAMILIES_V2, FAMILY_ALLOWED_CTA
from backend.silent import registry, canon, hooks as hooks_mod

BIAS = SILENT["mechanic_bias"]
ACTIVE = ["test", "elimination", "projection", "transformation", "revelation", "conseil", "preuve"]
DEPRECATED = ["comparison", "vote", "collection", "top3", "battle", "erreur", "pov",
              "comparison_4", "collection_4"]
BATCH = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "test_batch_v2.json")
EXPECTED_COUNTS = {"miroir": 4, "choix_force": 4, "projection": 3, "bascule": 3,
                   "revelation": 4, "conseil": 4, "preuve": 2}


def test_seven_active_families():
    assert set(FAMILIES_V2) == set(EXPECTED_COUNTS)
    for fam, spec in FAMILIES_V2.items():
        m = spec["mechanic"]
        assert registry.is_active(m), f"{fam}->{m} doit être active"
        assert BIAS.get(m, 0) > 0, f"{m} doit avoir un biais > 0"


def test_deprecated_mechanics_retired_but_kept():
    for m in DEPRECATED:
        assert m in registry.MECHANICS, f"{m} doit rester dans le code (rollback)"
        assert registry.MECHANICS[m].get("deprecated_v2") is True
        assert not registry.is_active(m)
        assert BIAS.get(m, 1.0) == 0.0, f"{m} doit être à 0.0 dans le mix"


def test_conseil_and_preuve_exist():
    for m in ("conseil", "preuve"):
        assert m in registry.MECHANICS and registry.is_active(m)
    assert "erreur" in registry.MECHANICS  # conservée, remplacée par conseil


def test_active_mix_has_no_static_catalog_layout():
    # aucune famille active ne doit utiliser une grille catalogue statique
    forbidden = {"split_2", "split_3", "grid_4"}
    for fam, spec in FAMILIES_V2.items():
        assert spec["visual_layout"] not in forbidden, fam
        for lay in registry.MECHANICS[spec["mechanic"]]["layouts"]:
            assert lay not in forbidden, f"{fam}:{lay}"


def test_new_hook_banks_are_canon_clean():
    for mech in ("conseil", "preuve"):
        for e in hooks_mod.load_hooks(mech):
            assert canon.is_clean(e["text"]), e["text"]


def test_batch_24_integrity():
    data = json.load(open(BATCH, encoding="utf-8"))["concepts"]
    assert len(data) == 24
    counts = {}
    seen_ids = set()
    for c in data:
        for k in ("concept_id", "family_id", "mechanic", "hook_id", "hook",
                  "cta_type", "visual_layout", "models"):
            assert k in c, f"clé manquante {k} dans {c.get('concept_id')}"
        assert c["concept_id"] not in seen_ids
        seen_ids.add(c["concept_id"])
        fam = c["family_id"]
        assert fam in FAMILIES_V2
        spec = FAMILIES_V2[fam]
        assert c["mechanic"] == spec["mechanic"]
        assert c["cta_type"] in FAMILY_ALLOWED_CTA[fam]
        assert c["visual_layout"] == spec["visual_layout"]
        assert len(c["models"]) == registry.MECHANICS[c["mechanic"]]["asset_count"]
        assert canon.is_clean(c["hook"]), c["hook"]
        counts[fam] = counts.get(fam, 0) + 1
    assert counts == EXPECTED_COUNTS
