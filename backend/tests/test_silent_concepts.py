"""Parser du DOSSIER_CONCEPTS.md : extraction hooks/cta par concept."""
from backend.silent import concepts

_SAMPLE = """# DOSSIER

## COMPARAISON_2
- fam: COMPARAISON | n: 2
- hook: Laquelle choisissez-vous ? | A ou B ? | Une seule à garder
- cta: Commente A ou B 👇 | Ton choix ?
- regle: 2 modèles différents

## VOTE_2
- fam: VOTE | n: 2
- hook: Votez A ou B | Qui mérite de gagner ?
- cta: Vote A 👇
"""


def test_parse_extracts_hooks_and_cta(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(_SAMPLE, encoding="utf-8")
    c = concepts.load_concepts.__wrapped__(str(p))  # bypass lru_cache
    assert "COMPARAISON_2" in c and "VOTE_2" in c
    assert c["COMPARAISON_2"]["hooks"] == [
        "Laquelle choisissez-vous ?", "A ou B ?", "Une seule à garder"]
    assert c["COMPARAISON_2"]["cta"] == ["Commente A ou B 👇", "Ton choix ?"]
    assert c["VOTE_2"]["hooks"] == ["Votez A ou B", "Qui mérite de gagner ?"]


def test_missing_file_returns_empty():
    assert concepts.load_concepts.__wrapped__("C:/nope/none.md") == {}
