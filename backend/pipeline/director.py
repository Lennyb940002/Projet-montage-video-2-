from backend.config import TRANSITIONS

def build_plan(tokens, n_sent, ranges, duration):
    """Timeline de décisions visuelles (extensible). Aujourd'hui : Ken Burns par
    clip, punch sur mots-clés, transitions aux cuts. Demain : enrichi par le
    moteur sémantique / B-roll sans toucher au reste."""
    motion = [{"kind": "kenburns", "start": s, "end": e} for (s, e) in ranges]
    for t in tokens:
        if t.get("kw"):
            motion.append({"kind": "punch", "start": t["start"]})
    transitions = [{"at": s, "type": TRANSITIONS["default_type"]} for (s, _e) in ranges[1:]]
    return {"motion": motion, "transitions": transitions}
