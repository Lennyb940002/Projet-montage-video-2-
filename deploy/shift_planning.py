"""Décale les dates du planning existant à partir d'une nouvelle date de début,
SANS re-rendre les vidéos (garde l'ordre + les 5 créneaux/jour). Pratique si la
date de départ en vacances change.  Usage : python deploy/shift_planning.py 2026-07-10"""
import os
import sys
import json
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANNING = os.path.join(ROOT, "stock", "planning.json")
SLOTS = ["07:00", "11:30", "15:00", "17:00", "21:00"]


def main(start):
    start_date = datetime.date.fromisoformat(start)
    plan = json.load(open(PLANNING, encoding="utf-8"))
    for i, it in enumerate(plan):
        day = start_date + datetime.timedelta(days=i // len(SLOTS))
        it["date"] = day.isoformat()
        it["heure"] = SLOTS[i % len(SLOTS)]
    json.dump(plan, open(PLANNING, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Planning décalé : {len(plan)} reels du {plan[0]['date']} au {plan[-1]['date']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python deploy/shift_planning.py YYYY-MM-DD"); sys.exit(1)
    main(sys.argv[1])
