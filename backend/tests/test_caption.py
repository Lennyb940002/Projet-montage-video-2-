from backend.pipeline.caption import generate_caption

TEXT = ("Pourquoi t'as pas de Rolex ? Parce que le prix fait peur. "
        "La qualité est au rendez-vous avec un verre saphir. "
        "Livraison en 24h. Écris SEIKO en commentaire.")

def test_accroche_is_first_sentence():
    c = generate_caption(TEXT)
    assert c["description"].splitlines()[0].startswith("Pourquoi t'as pas de Rolex")

def test_brand_hashtag_added():
    c = generate_caption(TEXT)
    assert "#rolex" in c["hashtags"]
    assert "#seiko" in c["hashtags"]

def test_cta_detected():
    c = generate_caption(TEXT)
    assert "commentaire" in c["description"].lower()

def test_benefits_prefixed():
    c = generate_caption(TEXT)
    assert "✅" in c["description"]

def test_hashtags_dedup_and_full():
    c = generate_caption(TEXT)
    assert len(c["hashtags"]) == len(set(c["hashtags"]))
    assert c["full"].endswith(" ".join(c["hashtags"]))

def test_empty_text_does_not_crash():
    c = generate_caption("")
    assert isinstance(c["full"], str)
