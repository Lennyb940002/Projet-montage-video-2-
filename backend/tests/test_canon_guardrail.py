import pytest
pytestmark = pytest.mark.skip(reason="V2 en pause — rollback V1 demande proprietaire 2026-07-03")
from backend.silent import canon


def test_bans_replica_and_mod_terms():
    for bad in ["Seiko Daytona Or rose", "une Daytona", "la Datejust",
                "c'est un mod", "des mods", "moddée main", "base SKX", "en DIY", "#seiko"]:
        assert not canon.is_clean(bad), bad
        assert canon.violations(bad)


def test_sanitize_removes_banned_terms():
    out = canon.sanitize("Découvre la Seiko Daytona Or rose, une belle mod #seiko")
    assert canon.is_clean(out)
    assert "daytona" not in out.lower()
    assert "#seiko" not in out.lower()


def test_no_false_positive_on_common_words():
    # « modèle », « mode », « commode » NE doivent PAS être bannis (piège du \bmod\b).
    for ok in ["Quel modèle te ressemble ?", "un style à la mode",
               "une commode en chêne", "cette montre est automatique"]:
        assert canon.is_clean(ok), ok
        assert canon.sanitize(ok) == ok


def test_sanitize_tags_drops_seiko_and_dedupes():
    tags = canon.sanitize_tags(["#seiko", "#Montre", "#montre", "#horlogerie"])
    assert all(t.lower() != "#seiko" for t in tags)
    assert len(tags) == len({t.lower() for t in tags})


def test_legacy_pipeline_emits_no_forbidden_hashtag():
    from backend.pipeline import caption as legacy
    from backend.config import LEGACY_BRAND_TAGS_DISABLED
    assert LEGACY_BRAND_TAGS_DISABLED == {}
    res = legacy.generate_caption(
        "Une superbe Rolex Daytona, une Seiko mod et une Omega. Prix 179 euros.")
    joined = " ".join(res["hashtags"]).lower()
    assert all(canon.is_clean(h) for h in res["hashtags"])
    assert "#rolex" not in joined and "#seiko" not in joined and "#daytona" not in joined


def test_bans_seikomod_and_luxury_hashtags():
    for bad in ["#seikomod", "#seiko", "#rolex", "#omega", "#patekphilippe",
                "#daytona", "#submariner", "#tissot", "#tagheuer"]:
        assert not canon.is_clean(bad), bad
        assert canon.is_clean(canon.sanitize(bad)), bad
    # les hashtags légitimes survivent
    for ok in ["#montreautomatique", "#flowerschrome", "#stylehomme", "#horlogerie"]:
        assert canon.is_clean(ok), ok
