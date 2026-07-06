"""Code CTA unique par post (FCxxx) : permet d'attribuer un DM à la publication
exacte qui l'a généré (« DM FC847 »). Compteur persistant, incrémental."""
import json
import os

_DIR = os.path.join(os.path.expanduser("~"), ".automontage")
_PATH = os.path.join(_DIR, "cta_counter.json")


def next_code():
    try:
        with open(_PATH, encoding="utf-8") as f:
            n = json.load(f).get("n", 100)
    except (FileNotFoundError, json.JSONDecodeError):
        n = 100
    n += 1
    os.makedirs(_DIR, exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump({"n": n}, f)
    return f"FC{n}"
