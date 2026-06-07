from backend.pipeline import sfx_plan as sp
from backend.pipeline.transcribe import Word

def test_detectors():
    assert sp.is_number("200€") and sp.is_number("3")
    assert sp.is_price("200€") and sp.is_price("euros")
    assert sp.is_watch_brand("Rolex") and sp.is_watch_brand("seiko")
    assert sp.is_question_word("Pourquoi") and sp.is_question_word("vraie ?")
    assert sp.is_cta("écris") and sp.is_cta("Commente")

def test_event_has_mix_params():
    e = sp._ev(1.0, "Whooshs")
    for k in ("time", "category", "gain_dB", "fade_in_ms", "fade_out_ms", "duck_voice_dB"):
        assert k in e

def test_generate_hook_impact_and_cta():
    words = [Word("Pourquoi", 0.0, 0.4, .9), Word("regarder", 0.4, 0.9, .9),
             Word("bien", 0.9, 1.2, .9),
             Word("une", 6.0, 6.2, .9), Word("Seiko", 6.2, 6.8, .9),  # marque isolée
             Word("à", 8.0, 8.1, .9), Word("200€", 8.1, 8.7, .9),     # prix isolé
             Word("écris", 12.0, 12.3, .9), Word("Seiko", 12.3, 12.9, .9)]
    phrases = [(0.0, 1.2), (6.0, 6.8), (8.0, 8.7), (12.0, 12.9)]
    cuts = [0.8, 1.6, 2.4, 6.0, 9.0]
    ev = sp.generate_sfx(words, phrases, cuts, duration=14.0)
    cats = {e["category"] for e in ev}
    assert any(e["time"] == 0.0 and e["category"] == "Impacts" for e in ev)  # impact d'ouverture
    assert "Whooshs" in cats                       # cuts du hook
    assert "Mechanical" in cats                    # marque isolée -> Mechanical
    assert any(abs(e["time"] - 8.1) < 0.3 and e["category"] == "Impacts" for e in ev)  # prix
    assert any(abs(e["time"] - 12.0) < 0.3 and e["category"] == "Impacts" for e in ev)  # CTA

def test_density_and_spacing():
    # 20 impacts collés -> doivent être fortement réduits
    words = [Word(str(i), i * 0.05, i * 0.05 + 0.03, .9) for i in range(20)]
    ev = sp.generate_sfx(words, [(0, 1)], [], duration=2.0)
    # cooldown impact 0.7s sur ~1s -> très peu d'évènements
    assert len(ev) <= 5
