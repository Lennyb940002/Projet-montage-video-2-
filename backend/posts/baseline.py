"""Empreinte de la POPULATION de contenu (banque de clips montres). Permet de
DÉTECTER un changement invisible (montre ajoutée, clip modifié) qui casserait la
comparabilité du dataset sans casser le système. Auto-capturé = vérité.

Usage :
  python -m backend.posts.baseline --save    # fige la population au début de fenêtre
  python -m backend.posts.baseline --check    # alerte si la banque a dérivé
"""
import datetime
import hashlib
import json
import os

from backend.config import SILENT

BASELINE_PATH = os.path.join(os.path.expanduser("~"), ".automontage", "baseline.json")
_EXT = (".mp4", ".mov", ".webm", ".m4v")


def bank_fingerprint(clips_dir=None):
    """{count, hash, by_model} de la banque de clips (population de contenu)."""
    clips_dir = clips_dir or SILENT["clips_dir"]
    files = []
    for root, _, fs in os.walk(clips_dir):
        for f in fs:
            if f.lower().endswith(_EXT):
                rel = os.path.relpath(os.path.join(root, f), clips_dir).replace("\\", "/")
                files.append(rel)
    files.sort()
    by_model = {}
    for rel in files:
        by_model[rel.split("/")[0]] = by_model.get(rel.split("/")[0], 0) + 1
    h = hashlib.sha1("\n".join(files).encode("utf-8")).hexdigest()[:12]
    return {"count": len(files), "hash": h, "by_model": by_model}


def save_baseline():
    fp = bank_fingerprint()
    data = {"date": datetime.date.today().isoformat(), "bank": fp}
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return data


def check():
    """Renvoie (stable: bool, message). Compare la banque actuelle à la baseline."""
    try:
        with open(BASELINE_PATH, encoding="utf-8") as f:
            saved = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False, "Aucune baseline figée (lance --save)."
    cur = bank_fingerprint()
    if cur["hash"] == saved["bank"]["hash"]:
        return True, f"OK — population stable ({cur['count']} clips, depuis {saved['date']})."
    return False, (f"⚠️ DÉRIVE : banque passée de {saved['bank']['count']} à {cur['count']} clips "
                   f"(baseline {saved['date']}). Comparabilité cassée → fenêtre à reset.\n"
                   f"   avant: {saved['bank']['by_model']}\n   après: {cur['by_model']}")


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        ok, msg = check()
        print(msg)
    else:
        d = save_baseline()
        print("Baseline population figée :", d["bank"]["count"], "clips |", d["bank"]["by_model"])
