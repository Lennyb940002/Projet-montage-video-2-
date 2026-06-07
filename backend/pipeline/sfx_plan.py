"""Plan de placement des SFX selon les règles d'un expert montage e-commerce :
hook dense, corps minimaliste, CTA re-dense, jamais un whoosh à chaque cut.
Entrée : words (objets .text/.start/.end), phrases [(start,end)], cuts [float], duration.
Sortie : [{time, category, gain_dB, fade_in_ms, fade_out_ms, duck_voice_dB}]
"""
import re

WATCH_BRANDS = {"rolex", "omega", "cartier", "patek", "audemars", "seiko",
                "tissot", "tag", "heuer", "daytona", "submariner", "datejust"}
QUESTION_WORDS = {"pourquoi", "comment", "combien"}
CTA_VERBS = {"écris", "écrivez", "ecris", "ecrivez", "commente", "commentez",
             "commande", "clique", "cliquez", "abonne", "suis", "envoie"}
TRANSITIONS = {"mais", "cependant", "pourtant"}  # "en revanche" géré à part

CATPARAMS = {
    "Impacts":       {"gain_dB": -8,  "fade_in_ms": 0,  "fade_out_ms": 120, "duck_voice_dB": -1},
    "Whooshs":       {"gain_dB": -12, "fade_in_ms": 10, "fade_out_ms": 80,  "duck_voice_dB": 0},
    "Risers":        {"gain_dB": -18, "fade_in_ms": 50, "fade_out_ms": 100, "duck_voice_dB": 0},
    "Drops":         {"gain_dB": -10, "fade_in_ms": 0,  "fade_out_ms": 150, "duck_voice_dB": -2},
    "Electronic":    {"gain_dB": -14, "fade_in_ms": 10, "fade_out_ms": 80,  "duck_voice_dB": 0},
    "Camera Sounds": {"gain_dB": -12, "fade_in_ms": 10, "fade_out_ms": 80,  "duck_voice_dB": 0},
    "Mechanical":    {"gain_dB": -11, "fade_in_ms": 10, "fade_out_ms": 90,  "duck_voice_dB": 0},
}
COOLDOWN = {"Impacts": 0.7, "Whooshs": 0.5, "Risers": 5.0,
            "Drops": 1.0, "Electronic": 0.5, "Camera Sounds": 0.5, "Mechanical": 0.5}
MIN_SAME = 0.30
MIN_ANY = 0.15
MAX_PER_10S = 6

def _norm(t):
    return re.sub(r"[^0-9a-zàâäçéèêëîïôöùûüœæ]", "", t.lower())

def is_number(t): return bool(re.search(r"\d", t))
def is_price(t):
    tl = t.lower()
    return any(s in tl for s in ("€", "eur", "euro", "$", "dollar"))
def is_watch_brand(t): return _norm(t) in WATCH_BRANDS
def is_question_word(t): return _norm(t) in QUESTION_WORDS or "?" in t
def is_cta(t): return _norm(t) in CTA_VERBS
def is_transition(t): return _norm(t) in TRANSITIONS

def find_first_strong_word(words):
    for w in words[:8]:
        if is_price(w.text) or is_number(w.text) or is_watch_brand(w.text) or is_question_word(w.text):
            return w
    return None

def find_cta_word(words):
    for w in words:
        if is_cta(w.text):
            return w
    return None

def _ev(time, category, gain_override=None):
    p = dict(CATPARAMS[category])
    if gain_override is not None:
        p["gain_dB"] = gain_override
    return {"time": round(max(0.0, time), 3), "category": category, **p}

def generate_sfx(words, phrases, cuts, duration, hook_dur=3.5):
    events = []
    # --- HOOK ---
    events.append(_ev(0.0, "Impacts"))
    fs = find_first_strong_word(words)
    if fs:
        events.append(_ev(fs.start - 0.45, "Risers"))
        events.append(_ev(fs.start, "Impacts"))
    # --- CUTS ---
    last_whoosh = -999.0
    for i, cut in enumerate(cuts):
        if cut <= hook_dur:
            events.append(_ev(cut - 0.08, "Whooshs")); last_whoosh = cut
        elif i % 2 == 0 and cut - last_whoosh > 1.5:
            events.append(_ev(cut - 0.08, "Whooshs")); last_whoosh = cut
    # --- MOTS-CLÉS ---
    for w in words:
        t = w.text
        if is_price(t):
            events.append(_ev(w.start, "Impacts", gain_override=-6))
        elif is_number(t):
            events.append(_ev(w.start, "Impacts"))
        elif is_watch_brand(t):
            events.append(_ev(w.start, "Mechanical"))
        elif is_question_word(t):
            events.append(_ev(w.start, "Electronic"))
    # --- CHANGEMENT DE SUJET (mais / cependant / pourtant) en début de phrase ---
    for (ps, _pe) in phrases:
        first = next((w for w in words if w.start >= ps - 0.05), None)
        if first and is_transition(first.text):
            events.append(_ev(ps, "Drops"))
            events.append(_ev(ps + 0.1, "Whooshs"))
    # --- CTA ---
    cta = find_cta_word(words)
    if cta:
        events.append(_ev(cta.start, "Impacts"))
        events.append(_ev(cta.start + 0.15, "Whooshs"))
    # --- FILTRES densité ---
    events = enforce_spacing(events)
    events = cap_density(events, MAX_PER_10S)
    return events

def enforce_spacing(events):
    out = []
    last_any = -999.0
    last_by_cat = {}
    for e in sorted(events, key=lambda x: x["time"]):
        c = e["category"]; t = e["time"]
        if t - last_any < MIN_ANY:
            continue
        cd = max(MIN_SAME, COOLDOWN.get(c, 0.0))
        if c in last_by_cat and t - last_by_cat[c] < cd:
            continue
        out.append(e); last_any = t; last_by_cat[c] = t
    return out

def cap_density(events, max_per_10s):
    out = []
    for e in sorted(events, key=lambda x: x["time"]):
        window = [k for k in out if e["time"] - k["time"] <= 10.0]
        if len(window) >= max_per_10s:
            continue
        out.append(e)
    return out
