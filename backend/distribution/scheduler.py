"""Scheduler des 4 créneaux quotidiens. Au déclenchement : génère une vidéo et
l'envoie sur Telegram pour validation."""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.distribution import orchestrator

SLOTS = [9, 12, 18, 22]
TIMEZONE = "Europe/Paris"
# Alterne le goal selon le créneau (3 engagement, 1 rétention le soir).
_GOAL_BY_SLOT = {9: "engagement", 12: "engagement", 18: "engagement", 22: "retention"}


def run_slot(app=None, hour=None, seed=None):
    """Génère une vidéo pour le créneau et l'envoie sur Telegram (si app fourni)."""
    import random
    goal = _GOAL_BY_SLOT.get(hour, "engagement")
    res = orchestrator.generate_for_slot(goal=goal,
                                         seed=seed if seed is not None else random.randrange(10**9))
    if app is not None:
        from backend.distribution.telegram_bot import send_for_approval
        asyncio.create_task(send_for_approval(app, res["pid"], res["video_path"], res["caption"]))
    return res


def build_scheduler(app):
    sch = AsyncIOScheduler(timezone=TIMEZONE)
    for h in SLOTS:
        sch.add_job(run_slot, CronTrigger(hour=h, minute=0, timezone=TIMEZONE),
                    kwargs={"app": app, "hour": h}, id=f"slot_{h}")
    return sch


def main():
    from backend.distribution.telegram_bot import build_app
    app = build_app()
    sch = build_scheduler(app)
    sch.start()
    app.run_polling()


if __name__ == "__main__":
    main()
