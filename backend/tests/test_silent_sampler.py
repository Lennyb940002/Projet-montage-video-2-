"""Sampler model-aware : montres distinctes par vidéo + exclusion des montres
récentes (anti-répétition)."""
import os, random
import pytest
from backend.silent import sampler


def _make_bank(root, models, clips_per=2):
    """Crée une banque <root>/<model>/clip_i.mp4 (sous-dossiers = montres)."""
    for m in models:
        d = os.path.join(root, m)
        os.makedirs(d, exist_ok=True)
        for i in range(clips_per):
            open(os.path.join(d, f"{m}_{i}.mp4"), "wb").write(b"x")


def test_sample_returns_distinct_models(tmp_path):
    _make_bank(str(tmp_path), ["A", "B", "C", "D"])
    out = sampler.sample({"count": 3, "filters": {}}, random.Random(1), str(tmp_path))
    models = {sampler.model_of(p) for p in out}
    assert len(out) == 3 and len(models) == 3   # 3 montres DIFFÉRENTES


def test_sample_excludes_recent_models(tmp_path):
    _make_bank(str(tmp_path), ["A", "B", "C", "D", "E"])
    out = sampler.sample({"count": 2, "filters": {}}, random.Random(2),
                         str(tmp_path), exclude_models={"A", "B"})
    models = {sampler.model_of(p) for p in out}
    assert models.isdisjoint({"A", "B"})        # aucune montre récente


def test_sample_relaxes_when_not_enough_fresh(tmp_path):
    # 3 modèles, on en exclut 2, mais on demande 3 -> doit relâcher (best-effort)
    _make_bank(str(tmp_path), ["A", "B", "C"])
    out = sampler.sample({"count": 3, "filters": {}}, random.Random(3),
                         str(tmp_path), exclude_models={"A", "B"})
    assert len({sampler.model_of(p) for p in out}) == 3   # produit quand même 3


def test_sample_seed_reproducible(tmp_path):
    _make_bank(str(tmp_path), ["A", "B", "C", "D"])
    a = sampler.sample({"count": 2, "filters": {}}, random.Random(42), str(tmp_path))
    b = sampler.sample({"count": 2, "filters": {}}, random.Random(42), str(tmp_path))
    assert a == b


def test_sample_raises_if_not_enough_models(tmp_path):
    _make_bank(str(tmp_path), ["A"])
    with pytest.raises(ValueError, match="not enough distinct models"):
        sampler.sample({"count": 2, "filters": {}}, random.Random(1), str(tmp_path))
