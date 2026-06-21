import backend.distribution.scheduler as sched


def test_slots_are_configured():
    assert sched.SLOTS == [9, 12, 18, 22]
    assert sched.TIMEZONE == "Europe/Paris"


def test_schedule_jobs_registers_four_daily(monkeypatch):
    calls = []

    class _JQ:
        def run_daily(self, cb, time, data, name):
            calls.append((name, data, time.hour))

    class _App:
        job_queue = _JQ()

    sched.schedule_jobs(_App())
    assert len(calls) == 4
    assert {h for _, h, _ in calls} == {9, 12, 18, 22}


def test_run_slot_uses_goal_by_slot(monkeypatch):
    seen = {}
    monkeypatch.setattr(sched.orchestrator, "generate_for_slot",
                        lambda goal, seed: seen.update(goal=goal) or {"pid": 1})
    sched.run_slot(hour=22, seed=1)
    assert seen["goal"] == "retention"      # 22h -> rétention
    sched.run_slot(hour=9, seed=1)
    assert seen["goal"] == "engagement"
