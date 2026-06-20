import backend.distribution.scheduler as sched


def test_slots_are_configured():
    assert sched.SLOTS == [9, 12, 18, 22]
    assert sched.TIMEZONE == "Europe/Paris"


def test_build_scheduler_registers_four_jobs(monkeypatch):
    monkeypatch.setattr(sched, "run_slot", lambda app=None, hour=None: None)
    scheduler = sched.build_scheduler(app=None)
    assert len(scheduler.get_jobs()) == 4
