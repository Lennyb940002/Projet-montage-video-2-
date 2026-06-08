"""Director — la SEULE source de décisions de montage.

Entrée  : events normalisés, tokens, ranges, duration
Sortie  : plan = {subtitles, motion, transitions}

Les renderers (subtitles.py, montage.py) sont purement exécutifs : ils consomment
ces structures sans aucune logique métier.
"""
from backend.config import TRANSITIONS, MOTION


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


def _decide_transitions(ranges):
    """Transitions length-preserving : fade d'entrée court à chaque clip
    (sauf le tout premier). Choisi par le Director, exécuté par montage."""
    return [{"kind": "fade_in", "clip_index": i, "dur": TRANSITIONS["dur"]}
            for i in range(1, len(ranges))]


# --- API publique ----------------------------------------------------------

def build_plan(events, tokens, n_sent, ranges, duration):
    """Construit le plan complet à partir des événements et de la timeline.
    Renvoie : {subtitles, motion, transitions}"""
    return {
        "subtitles":   _decide_subtitles(events, tokens, n_sent),
        "motion":      _decide_motion(events, ranges),
        "transitions": _decide_transitions(ranges),
    }
