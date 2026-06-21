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

SLOTS = [9, 12, 18, 22]
TIMEZONE = "Europe/Paris"
# Alterne le goal selon le créneau (3 engagement, 1 rétention le soir).
_GOAL_BY_SLOT = {9: "engagement", 12: "engagement", 18: "engagement", 22: "retention"}


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


def schedule_jobs(app):
    """Enregistre les 4 créneaux quotidiens sur la JobQueue du bot (Europe/Paris)."""
    tz = ZoneInfo(TIMEZONE) if ZoneInfo else None
    for h in SLOTS:
        app.job_queue.run_daily(
            _slot_job, time=datetime.time(hour=h, minute=0, tzinfo=tz),
            data=h, name=f"slot_{h}")
    return app.job_queue


def main():
    from backend.distribution.telegram_bot import build_app
    app = build_app()
    schedule_jobs(app)
    print(f"[scheduler] créneaux armés {SLOTS} ({TIMEZONE}) — bot en écoute.", flush=True)
    app.run_polling()


if __name__ == "__main__":
    main()
