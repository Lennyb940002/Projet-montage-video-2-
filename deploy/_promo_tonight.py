"""Attend l'heure cible (défaut 20:00, locale) puis poste UNE story promo.
Usage : PYTHONPATH=. python deploy/_promo_tonight.py [HH:MM]
"""
import datetime
import sys
import time

from backend.posts import promo


def main():
    hhmm = sys.argv[1] if len(sys.argv) > 1 else "20:00"
    hh, mm = (int(x) for x in hhmm.split(":"))
    now = datetime.datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    wait = (target - now).total_seconds()
    print(f"[promo] cible {target:%d/%m %H:%M} — attente {int(wait // 60)} min…", flush=True)
    while True:
        rem = (target - datetime.datetime.now()).total_seconds()
        if rem <= 0:
            break
        time.sleep(min(rem, 120))
    res = promo.post_promo()
    print(f"[promo] POSTÉ — modèle {res.get('model')} | ok={res.get('posted')}", flush=True)


if __name__ == "__main__":
    main()
