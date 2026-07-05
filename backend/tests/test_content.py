import json
import os
import random

from backend.silent import content

GMT = r"C:\Users\User\Downloads\Montage video\Banque video\GMT\clip1.mp4"
ORO = r"C:\Users\User\Downloads\Montage video\Banque video\Rainbow Or rose\c.mp4"


def test_detect_family():
    assert content.detect_family(GMT) == "gmt"
    assert content.detect_family(ORO) == "or_rose"
    assert content.detect_family(r"X\Inconnu\c.mp4") is None


def test_pick_labels_count_and_shape():
    labels, meta = content.pick_labels("test", (GMT, ORO, GMT), random.Random(1))
    assert len(labels) == 3
    assert all(isinstance(t, str) and c.startswith("&H") for t, c in labels)
    assert len(meta) == 3 and all(m["mode"] in ("coherent", "surprise") for m in meta)
    assert meta[0]["famille"] == "gmt"


def test_coherent_label_in_correct_bank():
    fam = json.load(open(os.path.join(os.path.dirname(content.__file__),
                    "banks", "familles.json"), encoding="utf-8"))
    coh = {x.lower() for x in fam["gmt"]["labels"]["profile"]["coherents"]}
    sur = {x.lower() for x in fam["gmt"]["labels"]["profile"]["surprise_acceptes"]}
    for s in range(60):
        labels, meta = content.pick_labels("test", (GMT, GMT, GMT), random.Random(s))
        for (txt, _), m in zip(labels, meta):
            pool = coh if m["mode"] == "coherent" else sur
            assert txt.lower() in pool, (s, txt, m)


def test_surprise_ratio_roughly_20pct():
    modes = []
    for s in range(400):
        _, meta = content.pick_labels("test", (GMT, GMT, GMT), random.Random(s))
        modes += [m["mode"] for m in meta]
    ratio = modes.count("surprise") / len(modes)
    assert 0.10 <= ratio <= 0.30, ratio


def test_pick_cta_rotates_types():
    rng = random.Random(0)
    used = []
    for _ in range(6):
        _text, typ = content.pick_cta("test", rng, used_types=used)
        used.append(typ)
    assert len(set(used)) >= 2


def test_deterministic():
    a = content.pick_labels("test", (GMT, ORO, GMT), random.Random(7))
    b = content.pick_labels("test", (GMT, ORO, GMT), random.Random(7))
    assert a == b
