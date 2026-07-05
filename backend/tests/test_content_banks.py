import json
import os

BANKS = os.path.join(os.path.dirname(__file__), "..", "silent", "banks")
FAMILLES = ["gmt", "or_rose", "saphir", "ruby", "silver"]
MODES = ["profile", "psycho", "trahison", "perception", "test_reveal"]


def _load(name):
    return json.load(open(os.path.join(BANKS, name), encoding="utf-8"))


def test_hooks_banks_non_empty():
    for f in ["hooks_test.json", "hooks_revelation_psy.json", "hooks_trahison.json",
              "hooks_perception.json", "hooks_test_perso.json"]:
        entries = _load(f)
        assert len(entries) >= 6, f
        assert all(e["text"] and e["angle"] for e in entries), f


def test_cta_typed():
    cta = _load("cta.json")
    types = {c["type"] for c in cta}
    assert {"comment", "dm", "question"} <= types
    assert all(c["text"] for c in cta)


def test_familles_cover_all_modes():
    fam = _load("familles.json")
    assert set(fam) == set(FAMILLES)
    for name, f in fam.items():
        assert f["dossiers"], name
        for mode in MODES:
            block = f["labels"][mode]
            assert block["coherents"], (name, mode)
            assert block["surprise_acceptes"], (name, mode)
            assert block["interdits"], (name, mode)


def test_surprise_never_in_interdits():
    fam = _load("familles.json")
    for name, f in fam.items():
        for mode in MODES:
            b = f["labels"][mode]
            inter = {x.lower() for x in b["interdits"]}
            assert not ({x.lower() for x in b["surprise_acceptes"]} & inter), (name, mode)
