"""Registre data-driven des mécaniques et layouts (V1). Source unique des
contraintes ; aucune décision ici (cf invariant architectural global).

Rollback 2026-07-03 : retour à la V1 qui tournait (les familles/layout séquence
V2 sont mis en pause à la demande du propriétaire ; le code V2 reste sur le
disque mais hors production)."""

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
    # --- Tier 1 : concepts du DOSSIER_CONCEPTS (layouts statiques + label_mode) ---
    "elimination": {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                    "hook_file": "elimination.json", "default_duration": 6.0,
                    "label_mode": "number"},
    "top3":        {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                    "hook_file": "top3.json", "default_duration": 6.0,
                    "label_mode": "podium"},
    "test":        {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                    "hook_file": "hooks_test.json", "default_duration": 6.0,
                    "label_mode": "profile"},
    # Projection / occasion (réf stratégie 22/06) : "laquelle pour un mariage ?"
    "projection":  {"goal": "engagement", "asset_count": 2, "layouts": ["split_2"],
                    "hook_file": "projection.json", "default_duration": 6.0,
                    "label_mode": "model_name"},
    "battle":      {"goal": "engagement", "asset_count": 2, "layouts": ["split_2"],
                    "hook_file": "battle.json", "default_duration": 6.0,
                    "label_mode": "category"},
    "transformation": {"goal": "engagement", "asset_count": 2, "layouts": ["split_2"],
                       "hook_file": "transformation.json", "default_duration": 6.0,
                       "label_mode": "before_after"},
    "erreur":      {"goal": "engagement", "asset_count": 2, "layouts": ["split_2"],
                    "hook_file": "erreur.json", "default_duration": 6.0,
                    "label_mode": "wrong_right"},
    "pov":         {"goal": "retention", "asset_count": 1, "layouts": ["single"],
                    "hook_file": "pov.json", "default_duration": 5.0,
                    "label_mode": "model_name"},
    "comparison_4": {"goal": "engagement", "asset_count": 4, "layouts": ["grid_4"],
                     "hook_file": "comparison.json", "default_duration": 6.0,
                     "label_mode": "number"},
    "collection_4": {"goal": "engagement", "asset_count": 4, "layouts": ["grid_4"],
                     "hook_file": "collection.json", "default_duration": 6.0,
                     "label_mode": "number"},
    # --- Formats 1A (guide 2026-07-05) : 3 montres, labels via banques familles ---
    "revelation_psy": {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                       "hook_file": "hooks_revelation_psy.json", "default_duration": 6.0,
                       "label_mode": "psycho"},
    "trahison":       {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                       "hook_file": "hooks_trahison.json", "default_duration": 6.0,
                       "label_mode": "trahison"},
    "perception":     {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                       "hook_file": "hooks_perception.json", "default_duration": 6.0,
                       "label_mode": "perception"},
    "test_perso":     {"goal": "engagement", "asset_count": 3, "layouts": ["split_3"],
                       "hook_file": "hooks_test_perso.json", "default_duration": 6.0,
                       "label_mode": "test_reveal"},
}

LAYOUTS = {
    "split_2": {"asset_count": 2},
    "split_3": {"asset_count": 3},
    "grid_4":  {"asset_count": 4},
    "reveal":  {"asset_count": 1},
    "single":  {"asset_count": 1},
    # layouts V2 (en pause) — gardés pour compat du renderer séquence
    "sequence_2": {"asset_count": 2},
    "sequence_3": {"asset_count": 3},
}


def mechanics_for_goal(goal):
    """Liste des mécaniques dont le goal correspond. Vide si aucun (P1 géré en aval)."""
    return [name for name, m in MECHANICS.items() if m["goal"] == goal]


def is_active(mechanic):
    """Compat V2 (en pause) : en V1 toute mécanique du registre est disponible."""
    return mechanic in MECHANICS
