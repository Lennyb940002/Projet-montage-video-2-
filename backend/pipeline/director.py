"""Director — la SEULE source de décisions de montage.

Entrée  : events normalisés, tokens, ranges, duration
Sortie  : plan = {subtitles, motion, transitions}

Les renderers (subtitles.py, montage.py) sont purement exécutifs : ils consomment
ces structures sans aucune logique métier.
"""
from backend.config import TRANSITIONS, MOTION, MUSIC as MUSIC_CFG
from backend.pipeline.sfx_plan import (
    is_cta as _is_cta,
    is_price as _is_price,
    is_number as _is_number,
    is_watch_brand as _is_watch_brand,
    _norm as _norm_word,
)
from backend.pipeline.keywords import SUPERLATIVES


# --- Helpers ---------------------------------------------------------------

# Rotation de zoom de base (Motion V1 robuste — pas de zoompan animé)
_ZOOM_ROTATION = (1.05, 1.10, 1.15, 1.20)
_MAXWORDS = 3


def _chunks_by_sentence(tokens, n_sent, maxwords=_MAXWORDS):
    out = []
    for si in range(n_sent):
        ws = [t for t in tokens if t["sent"] == si]
        for c in range(0, len(ws), maxwords):
            out.append(ws[c:c + maxwords])
    return out


def _is_kw_at(events, start, end):
    """Y a-t-il un évènement keyword qui chevauche [start,end] ? Renvoie l'évènement ou None."""
    for e in events:
        if e["type"] == "keyword" and not (e["end"] <= start or e["start"] >= end):
            return e
    return None


def _clip_index_for(t, ranges):
    for i, (s, e) in enumerate(ranges):
        if s <= t < e:
            return i
    return None


# --- Décisions -------------------------------------------------------------

def _decide_subtitles(events, tokens, n_sent):
    """Une SubLine par mot actif. Chaque mot reçoit un rôle :
       active | kw_active | kw_idle | normal."""
    plan_subs = []
    chunks = _chunks_by_sentence(tokens, n_sent)
    # marqueur : un mot est "kw" si un évènement keyword chevauche sa fenêtre
    kw_flag = [_is_kw_at(events, t["start"], t["end"]) is not None for t in tokens]
    # index mot global pour retrouver le flag
    idx_of = {id(t): i for i, t in enumerate(tokens)}
    for ci, chunk in enumerate(chunks):
        for a in range(len(chunk)):
            wstart = chunk[a]["start"]
            wend = chunk[a + 1]["start"] if a + 1 < len(chunk) else chunk[a]["end"]
            if wend <= wstart:
                wend = wstart + 0.08
            words = []
            for j, wd in enumerate(chunk):
                is_kw = kw_flag[idx_of[id(wd)]]
                if j == a and is_kw:
                    role = "kw_active"
                elif j == a:
                    role = "active"
                elif is_kw:
                    role = "kw_idle"
                else:
                    role = "normal"
                words.append({"disp": wd["disp"], "role": role})
            plan_subs.append({"start": wstart, "end": wend, "words": words})
    return plan_subs


def _decide_motion(events, ranges):
    """Motion V1 robuste :
       - 1 zoom_clip par clip (rotation de niveaux pour donner de la vie)
       - 1 punch par keyword tombant dans un clip
       - 1 shake par keyword 'high' (court, doux)
    """
    motion = []
    # Zoom de base par clip (rotation)
    for i, (s, e) in enumerate(ranges):
        motion.append({
            "kind": "zoom_clip",
            "clip_index": i,
            "zoom": _ZOOM_ROTATION[i % len(_ZOOM_ROTATION)],
        })
    # Punch + shake sur les keywords
    seen_punch_per_clip = set()
    for ev in events:
        if ev["type"] != "keyword":
            continue
        ci = _clip_index_for(ev["start"], ranges)
        if ci is None:
            continue
        local = ev["start"] - ranges[ci][0]
        # Un seul punch par clip (priorité au premier dans la fenêtre)
        if ci not in seen_punch_per_clip:
            motion.append({
                "kind": "punch",
                "clip_index": ci,
                "at_local": local,
                "zoom_to": MOTION["punch_zoom"],
                "dur": 0.35,
            })
            seen_punch_per_clip.add(ci)
        if ev.get("importance") == "high":
            motion.append({
                "kind": "shake",
                "clip_index": ci,
                "at_local": local,
                "amp_px": MOTION["shake_px"],
                "dur": 0.3,
            })
    return motion


def _decide_transitions(events, ranges):
    """Transitions length-preserving sélectionnées selon le contexte :
       - zoom_punch_in si le clip commence sur un keyword 'high' (entrée dynamique)
       - fade_in sinon (entrée calme)."""
    out = []
    for i in range(1, len(ranges)):
        s, _e = ranges[i]
        # Premier keyword qui ouvre ce clip (dans les 0.5 premières secondes)
        opens_on_kw = any(
            ev["type"] == "keyword" and ev.get("importance") == "high"
            and s <= ev["start"] < s + 0.5
            for ev in events
        )
        if opens_on_kw:
            out.append({"kind": "zoom_punch_in", "clip_index": i, "dur": 0.18})
        else:
            out.append({"kind": "fade_in", "clip_index": i, "dur": TRANSITIONS["dur"]})
    return out


# --- Décisions musique (T4 : signaux + scoring + helpers) ------------------

def _voice_active_events(tokens, gap_threshold=1.0):
    """Agrège les tokens en plages parlées contiguës.
    Un trou >= gap_threshold (s) entre deux tokens ouvre une nouvelle plage."""
    if not tokens:
        return []
    out = []
    cur_s, cur_e = tokens[0]["start"], tokens[0]["end"]
    for t in tokens[1:]:
        if t["start"] - cur_e >= gap_threshold:
            out.append({"type": "voice_active", "start": cur_s, "end": cur_e})
            cur_s = t["start"]
        cur_e = max(cur_e, t["end"])
    out.append({"type": "voice_active", "start": cur_s, "end": cur_e})
    return out


def _pre_cta_gap_event(events, gap_dur=None):
    """Crée un event pre_cta_gap juste avant le PREMIER keyword CTA détecté.
    None si aucun CTA dans les events."""
    g = MUSIC_CFG["pre_cta_gap_s"] if gap_dur is None else gap_dur
    for ev in events:
        if ev.get("type") == "keyword" and _is_cta(ev.get("label", "")):
            return {
                "type": "pre_cta_gap",
                "start": max(0.0, ev["start"] - g),
                "end": ev["start"],
                "importance": "high",
            }
    return None


def _score_music_category(events, duration):
    """Heuristique simple basée sur les events keyword existants.

    Renvoie un dict EXPLICABLE :
      {
        "category": "luxury" | "hype",
        "confidence": float,
        "reason": [str, ...],
        "fallback_used": bool,
        "signals": {n_cta, n_price, n_number, n_brand, n_superlative,
                    n_high, density_high, duration},
        "scores": {"luxury": float, "hype": float},
      }

    Le champ `scores` est TOUJOURS présent (même en fallback) pour qu'on
    puisse comprendre dans 3 semaines pourquoi telle décision a été prise.
    """
    kw = [e for e in events if e.get("type") == "keyword"]
    n_cta = sum(1 for e in kw if _is_cta(e.get("label", "")))
    n_price = sum(1 for e in kw if _is_price(e.get("label", "")))
    n_number = sum(1 for e in kw if _is_number(e.get("label", "")))
    n_brand = sum(1 for e in kw if _is_watch_brand(e.get("label", "")))
    n_superlative = sum(1 for e in kw if _norm_word(e.get("label", "")) in SUPERLATIVES)
    n_high = sum(1 for e in kw if e.get("importance") == "high")
    density_high = (n_high / len(kw)) if kw else 0.0
    signals = {
        "n_cta": n_cta, "n_price": n_price, "n_number": n_number,
        "n_brand": n_brand, "n_superlative": n_superlative,
        "n_high": n_high, "density_high": density_high, "duration": duration,
    }

    # Score Hype
    hype_score, hype_reasons = 0.0, []
    if n_cta >= 2:
        hype_score += 0.30; hype_reasons.append(f"{n_cta} CTA")
    if n_price + n_number >= 2:
        hype_score += 0.25; hype_reasons.append(f"{n_price + n_number} chiffres/prix")
    if duration < 20:
        hype_score += 0.15; hype_reasons.append("duration < 20s")
    if density_high >= 0.5 and kw:
        hype_score += 0.30; hype_reasons.append("densité events high")

    # Score Luxury
    lux_score, lux_reasons = 0.0, []
    if n_brand >= 1:
        lux_score += 0.35; lux_reasons.append("brand detected")
    if n_superlative >= 1:
        lux_score += 0.30; lux_reasons.append("superlative detected")
    if n_cta <= 1:
        lux_score += 0.15; lux_reasons.append("peu de CTA")
    if duration >= 20:
        lux_score += 0.20; lux_reasons.append("duration >= 20s")

    scores = {"luxury": round(lux_score, 2), "hype": round(hype_score, 2)}

    if hype_score >= lux_score:
        cat, conf, reasons = "hype", hype_score, hype_reasons
    else:
        cat, conf, reasons = "luxury", lux_score, lux_reasons

    if conf < MUSIC_CFG["confidence_threshold"]:
        return {
            "category": MUSIC_CFG["category_default"],
            "confidence": round(conf, 2),
            "reason": ["low confidence fallback"],
            "fallback_used": True,
            "signals": signals,
            "scores": scores,
        }
    return {
        "category": cat,
        "confidence": round(conf, 2),
        "reason": reasons,
        "fallback_used": False,
        "signals": signals,
        "scores": scores,
    }


# --- API publique ----------------------------------------------------------

def build_plan(events, tokens, n_sent, ranges, duration):
    """Construit le plan complet à partir des événements et de la timeline.
    Renvoie : {subtitles, motion, transitions}"""
    return {
        "subtitles":   _decide_subtitles(events, tokens, n_sent),
        "motion":      _decide_motion(events, ranges),
        "transitions": _decide_transitions(events, ranges),
    }
