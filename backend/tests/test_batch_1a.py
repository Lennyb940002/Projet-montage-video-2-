import importlib.util
import os
from collections import Counter

_P = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "generate_batch_1a.py")
_spec = importlib.util.spec_from_file_location("gen1a", _P)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_plan_distribution():
    plan = gen.build_plan()
    c = Counter(p["mechanic"] for p in plan)
    assert c == {"test": 10, "revelation_psy": 8, "trahison": 6,
                 "perception": 4, "test_perso": 2}
    assert len(plan) == 30


def test_recipes_anti_repetition():
    recipes = gen.build_recipes(seed=42)
    assert len(recipes) == 30
    # hook jamais utilisé plus de 2 fois par mécanique
    seen = {}
    for r in recipes:
        seen.setdefault(r.mechanic, Counter())[r.hook] += 1
    for mech, cnt in seen.items():
        assert max(cnt.values()) <= 2, (mech, cnt)
    # aucun trio de montres identique (même ensemble ordonné)
    trios = [tuple(r.assets) for r in recipes]
    assert len(set(trios)) == len(trios)


def test_manifest_fields():
    entry = gen.manifest_entry(gen.build_recipes(seed=1)[0], "output/x.mp4")
    for k in ["mecanique", "hook", "montres", "familles_detectees", "labels",
              "cta", "mode_coherence", "chemin_export"]:
        assert k in entry
