"""Scheduler des 4 créneaux quotidiens. Utilise la JobQueue du bot Telegram
(même boucle asyncio que le polling) -> pas de bug cross-loop. Au déclenchement :
génère une vidéo (dans un thread, pour ne pas bloquer la boucle) et l'envoie sur
Telegram pour validation."""
import asyncio
import random
import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:                       # pragma: no cover
    ZoneInfo = None
from backend.distribution import orchestrator

# Créneaux quotidiens (heure, minute), Europe/Paris.
SLOTS = [(7, 0), (11, 30), (15, 0), (17, 0), (21, 0)]
TIMEZONE = "Europe/Paris"
# Alterne le goal selon le créneau (engagement la journée, rétention le soir).
_GOAL_BY_SLOT = {7: "engagement", 11: "engagement", 15: "engagement",
                 17: "engagement", 21: "retention"}
# Carrousels (heure, minute, type) — auto-direct, sans validation Telegram.
CAROUSEL_SLOTS = [(12, 0, "value"), (18, 0, "objection")]
# Stories promo (photos réelles) — 3/jour bien espacées, cycle des 13 modèles.
PROMO_SLOTS = [(9, 0), (14, 0), (20, 0)]


def run_slot(goal=None, hour=None, seed=None):
    """Génère une vidéo pour le créneau (SYNC, ffmpeg). Renvoie le dict
    orchestrateur {pid, video_path, caption}."""
    goal = goal or _GOAL_BY_SLOT.get(hour, "engagement")
    return orchestrator.generate_for_slot(
        goal=goal, seed=seed if seed is not None else random.randrange(10 ** 9))


async def _slot_job(context):
    """Job JobQueue : génère (hors boucle via to_thread) puis envoie Telegram."""
    hour = context.job.data
    res = await asyncio.to_thread(run_slot, hour=hour)
    from backend.distribution.telegram_bot import send_for_approval
    await send_for_approval(context.application, res["pid"], res["video_path"], res["caption"])


async def _carousel_job(context):
    """Job carrousel : génère + publie (hors boucle via to_thread). Auto-direct."""
    kind = context.job.data
    from backend.posts import orchestrator as posts_orch
    res = await asyncio.to_thread(posts_orch.generate_and_post, kind)
    print(f"[carousel:{kind}] {res.get('id')} ({res.get('theme')}) "
          f"posté={res.get('posted')}", flush=True)


async def _promo_job(context):
    """Story promo (photo réelle) auto — cycle des 13 modèles, jamais 2x le même d'affilée."""
    from backend.posts import promo
    res = await asyncio.to_thread(promo.post_promo)
    print(f"[promo] {res.get('photo')} ({res.get('model')}) posté={res.get('posted')}", flush=True)


async def _analytics_job(context):
    """Snapshot quotidien des métriques IG -> CSV (série temporelle data-driven)."""
    from backend.posts import analytics
    n = await asyncio.to_thread(analytics.snapshot)
    print(f"[analytics] snapshot : {n} posts loggés", flush=True)


def schedule_jobs(app):
    """Enregistre les créneaux quotidiens (vidéos + carrousels + snapshot analytics)."""
    tz = ZoneInfo(TIMEZONE) if ZoneInfo else None
    for h, m in SLOTS:
        app.job_queue.run_daily(
            _slot_job, time=datetime.time(hour=h, minute=m, tzinfo=tz),
            data=h, name=f"slot_{h}_{m}")
    for h, m, kind in CAROUSEL_SLOTS:
        app.job_queue.run_daily(
            _carousel_job, time=datetime.time(hour=h, minute=m, tzinfo=tz),
            data=kind, name=f"carousel_{kind}")
    for h, m in PROMO_SLOTS:
        app.job_queue.run_daily(
            _promo_job, time=datetime.time(hour=h, minute=m, tzinfo=tz),
            data=None, name=f"promo_{h}_{m}")
    app.job_queue.run_daily(
        _analytics_job, time=datetime.time(hour=23, minute=0, tzinfo=tz),
        data=None, name="analytics")
    return app.job_queue


def _delay_until_today(hour, minute, grace=3.0):
    """Secondes jusqu'à hh:mm aujourd'hui (Europe/Paris). Si l'heure est déjà
    passée, renvoie 'grace' (déclenchement quasi immédiat = créneau en retard)."""
    tz = ZoneInfo(TIMEZONE) if ZoneInfo else None
    now = datetime.datetime.now(tz)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    delay = (target - now).total_seconds()
    return delay if delay > 0 else grace


def schedule_today(app, slots):
    """Créneaux EXCEPTIONNELS du jour (one-off, ne se répètent pas demain)."""
    for h, m in slots:
        app.job_queue.run_once(_slot_job, _delay_until_today(h, m),
                               data=h, name=f"once_{h}_{m}")
    return app.job_queue


def main(slots_today=None):
    from backend.distribution.telegram_bot import build_app
    app = build_app()
    if slots_today:
        schedule_today(app, slots_today)
        print(f"[scheduler] créneaux EXCEPTIONNELS du jour {slots_today} "
              f"({TIMEZONE}) — bot en écoute.", flush=True)
    else:
        schedule_jobs(app)
        print(f"[scheduler] vidéos {SLOTS} + carrousels {CAROUSEL_SLOTS} "
              f"+ promos {PROMO_SLOTS} ({TIMEZONE}) — bot en écoute.", flush=True)
    app.run_polling()


if __name__ == "__main__":
    import sys
    _args = sys.argv[1:]
    if _args and _args[0] == "--today":
        _slots = []
        for _a in _args[1:]:
            _h, _, _m = _a.partition(":")
            _slots.append((int(_h), int(_m or 0)))
        main(slots_today=_slots)
    else:
        main()
