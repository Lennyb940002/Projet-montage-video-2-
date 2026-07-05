import importlib.util
import os
import random
from collections import Counter

_P = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "generate_special_formats.py")
_spec = importlib.util.spec_from_file_location("genspecial", _P)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_choix_quatuors_uniques_et_4_modeles():
    plan = gen.build_choix(4, random.Random(1))
    assert len(plan) == 4
    quatuors = [frozenset(p["models"]) for p in plan]
    assert len(set(quatuors)) == len(quatuors)          # jamais le même quatuor
    assert all(len(set(p["models"])) == 4 for p in plan)  # 4 modèles distincts / reel
    hooks = Counter(p["hook"] for p in plan)
    assert max(hooks.values()) <= 2                     # hook <=2


def test_devine_montres_variees_et_prix():
    plan = gen.build_devine(4, random.Random(1))
    assert len(plan) == 4
    assert all(p["prix"] == gen.PRIX for p in plan)
    hooks = Counter(p["hook"] for p in plan)
    assert max(hooks.values()) <= 2


def test_manifests_have_fields():
    c = gen.manifest_choix(gen.build_choix(1, random.Random(2))[0], "out/x.mp4")
    d = gen.manifest_devine(gen.build_devine(1, random.Random(2))[0], "out/y.mp4")
    for k in ["concept", "hook", "montres", "actions", "export"]:
        assert k in c
    for k in ["concept", "hook", "montre", "prix_revele", "cta", "export"]:
        assert k in d
