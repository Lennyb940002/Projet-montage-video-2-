"""Registre data-driven des mécaniques et layouts (V1). Source unique des
contraintes ; aucune décision ici (cf invariant architectural global)."""

MECHANICS = {
    "comparison": {"goal": "engagement", "asset_count": 2,
                   "layouts": ["split_2"], "hook_file": "comparison.json",
                   "default_duration": 6.0},
    "vote":       {"goal": "engagement", "asset_count": 2,
                   "layouts": ["split_2"], "hook_file": "vote.json",
                   "default_duration": 6.0},
    "revelation": {"goal": "retention",  "asset_count": 1,
                   "layouts": ["reveal"], "hook_file": "revelation.json",
                   "default_duration": 5.0},
    # V1.1 — format 3 montres (réf : showcase "team 🤍/💗/💙")
    "collection": {"goal": "engagement", "asset_count": 3,
                   "layouts": ["split_3"], "hook_file": "collection.json",
                   "default_duration": 6.0},
}

LAYOUTS = {
    "split_2": {"asset_count": 2},
    "split_3": {"asset_count": 3},
    "reveal":  {"asset_count": 1},
}


def mechanics_for_goal(goal):
    """Liste des mécaniques dont le goal correspond. Vide si aucun (P1 géré en aval)."""
    return [name for name, m in MECHANICS.items() if m["goal"] == goal]
