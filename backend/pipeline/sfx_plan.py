"""Plan de placement + alignement des SFX (règles d'expert montage e-commerce).
Chaque évènement porte un 'align' interprété par le moteur :
  - "attack" : l'attaque du son tombe sur 'time' (lead-in retiré).
  - "peak"   : le PIC du son tombe sur 'time' (ex: whoosh calé sur le cut).
  - "end"    : le son SE TERMINE à 'time' - 0.03 (ex: riser qui monte vers le mot).
Sortie : [{time, category, align, gain_dB, fade_in_ms, fade_out_ms, duck_voice_dB}]
"""
import re

WATCH_BRANDS = {"rolex", "omega", "cartier", "patek", "audemars", "seiko",
                "tissot", "tag", "heuer", "daytona", "submariner", "datejust"}
QUESTION_WORDS = {"pourquoi", "comment", "combien"}
CTA_VERBS = {"écris", "écrivez", "ecris", "ecrivez", "commente", "commentez",
             "commande", "clique", "cliquez", "abonne", "suis", "envoie"}
TRANSITIONS = {"mais", "cependant", "pourtant"}

CATPARAMS = {
    "Impacts":       {"gain_dB": -8,  "fade_in_ms": 0,  "fade_out_ms": 120, "duck_voice_dB": -2},
    "Whooshs":       {"gain_dB": -12, "fade_in_ms": 10, "fade_out_ms": 80,  "duck_voice_dB": 0},
    "Risers":        {"gain_dB": -18, "fade_in_ms": 50, "fade_out_ms": 100, "duck_voice_dB": 0},
    "Drops":         {"gain_dB": -10, "fade_in_ms": 0,  "fade_out_ms": 150, "duck_voice_dB": -3},
    "Electronic":    {"gain_dB": -14, "fade_in_ms": 10, "fade_out_ms": 80,  "duck_voice_dB": 0},
    "Mechanical":    {"gain_dB": -11, "fade_in_ms": 10, "fade_out_ms": 90,  "duck_voice_dB": -1},
}
COOLDOWN = {"Impacts": 0.7, "Whooshs": 0.5, "Risers": 5.0,
            "Drops": 1.0, "Electronic": 0.5, "Mechanical": 0.5}
MIN_SAME, MIN_ANY = 0.30, 0.15
SNAP = {"Impacts": 0.08, "Drops": 0.10, "Mechanical": 0.08, "Electronic": 0.08}
GAP_MIN = 0.06          # pause considérée comme "trou" exploitable
HOOK_MAX, BODY_MAX = 8, 4
PRE_CTA_GAP = 1.2       # silence SFX juste avant le CTA

def _norm(t): return re.sub(r"[^0-9a-zàâäçéèêëîïôöùûüœæ]", "", t.lower())
def is_number(t): return bool(re.search(r"\d", t))
def is_price(t):
    tl = t.lower(); return any(s in tl for s in ("€", "eur", "euro", "$", "dollar"))
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

def _ev(time, category, align="attack", gain_override=None):
    p = dict(CATPARAMS[category])
    if gain_override is not None:
        p["gain_dB"] = gain_override
    return {"time": round(max(0.0, time), 3), "category": category, "align": align, **p}

def _pauses(words):
    out = []
    for i in range(len(words) - 1):
        if words[i + 1].start - words[i].end >= GAP_MIN:
            out.append(words[i].end)
    return out

def _snap(t, pauses, max_shift):
    best, bd = None, max_shift
    for p in pauses:
        if abs(p - t) <= bd:
            bd = abs(p - t); best = p
    return best if best is not None else t

def generate_sfx(words, phrases, cuts, duration, hook_dur=3.5):
    events = []
    # --- HOOK ---
    events.append(_ev(0.0, "Impacts"))
    fs = find_first_strong_word(words)
    if fs:
        events.append(_ev(fs.start, "Risers", align="end"))
        events.append(_ev(fs.start + 0.02, "Impacts"))
    # --- CUTS (whoosh, pic calé sur le cut) ---
    last_whoosh = -999.0
    for i, cut in enumerate(cuts):
        if cut <= hook_dur:
            events.append(_ev(cut, "Whooshs", align="peak")); last_whoosh = cut
        elif i % 2 == 0 and cut - last_whoosh > 1.5:
            events.append(_ev(cut, "Whooshs", align="peak")); last_whoosh = cut
    # --- MOTS-CLÉS (attaque sur mot + 20 ms) ---
    for w in words:
        t = w.text
        if is_price(t):
            events.append(_ev(w.start + 0.02, "Impacts", gain_override=-6))
        elif is_number(t):
            events.append(_ev(w.start + 0.02, "Impacts"))
        elif is_watch_brand(t):
            events.append(_ev(w.start + 0.02, "Mechanical"))
        elif is_question_word(t):
            events.append(_ev(w.start + 0.02, "Electronic"))
    # --- CHANGEMENT DE SUJET ---
    for (ps, _pe) in phrases:
        first = next((w for w in words if w.start >= ps - 0.05), None)
        if first and is_transition(first.text):
            events.append(_ev(ps - 0.05, "Drops"))
            events.append(_ev(ps, "Whooshs", align="peak"))
    # --- CTA ---
    cta = find_cta_word(words)
    if cta:
        events.append(_ev(cta.start + 0.02, "Impacts"))
        events.append(_ev(cta.start + 0.15, "Whooshs", align="peak"))

    # --- SNAP sur micro-pauses (évènements "attaque" sur mots) ---
    pauses = _pauses(words)
    for e in events:
        if e["align"] == "attack":
            e["time"] = round(_snap(e["time"], pauses, SNAP.get(e["category"], 0.08)), 3)

    events = enforce_spacing(events)
    if cta:
        events = _pre_cta_gap(events, cta.start)
    events = cap_density_zoned(events, hook_dur)
    return events

def enforce_spacing(events):
    out, last_any, last_by_cat = [], -999.0, {}
    for e in sorted(events, key=lambda x: x["time"]):
        c, t = e["category"], e["time"]
        if t - last_any < MIN_ANY:
            continue
        if c in last_by_cat and t - last_by_cat[c] < max(MIN_SAME, COOLDOWN.get(c, 0.0)):
            continue
        out.append(e); last_any = t; last_by_cat[c] = t
    return out

def _pre_cta_gap(events, cta_time):
    lo = cta_time - PRE_CTA_GAP
    return [e for e in events if not (lo <= e["time"] < cta_time)]

def cap_density_zoned(events, hook_dur):
    out = []
    for e in sorted(events, key=lambda x: x["time"]):
        if e["time"] < hook_dur:
            out.append(e); continue
        window = [k for k in out if k["time"] >= hook_dur and e["time"] - k["time"] <= 10.0]
        if len(window) < BODY_MAX:
            out.append(e)
    return out
