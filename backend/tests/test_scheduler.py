import backend.distribution.scheduler as sched


def test_slots_are_configured():
    assert sched.SLOTS == [(7, 0), (11, 30), (15, 0), (17, 0), (21, 0)]
    assert sched.TIMEZONE == "Europe/Paris"


def test_schedule_jobs_registers_videos_and_carousels(monkeypatch):
    calls = []

    class _JQ:
        def run_daily(self, cb, time, data, name):
            calls.append((name, data, time.hour, time.minute))

    class _App:
        job_queue = _JQ()

    sched.schedule_jobs(_App())
    # 5 vidéos + 2 carrousels + 3 promos + 1 snapshot analytics
    assert len(calls) == 11
    video = {(h, m) for n, _, h, m in calls if n.startswith("slot_")}
    assert video == {(7, 0), (11, 30), (15, 0), (17, 0), (21, 0)}
    carousels = {(d, h, m) for n, d, h, m in calls if n.startswith("carousel_")}
    assert carousels == {("value", 12, 0), ("objection", 18, 0)}
    promos = {(h, m) for n, _, h, m in calls if n.startswith("promo_")}
    assert promos == {(9, 0), (14, 0), (20, 0)}
    assert any(n == "analytics" and h == 23 for n, _, h, m in calls)


def test_carousel_slots_configured():
    assert sched.CAROUSEL_SLOTS == [(12, 0, "value"), (18, 0, "objection")]
    assert sched.PROMO_SLOTS == [(9, 0), (14, 0), (20, 0)]


def test_run_slot_uses_goal_by_slot(monkeypatch):
    seen = {}
    monkeypatch.setattr(sched.orchestrator, "generate_for_slot",
                        lambda goal, seed: seen.update(goal=goal) or {"pid": 1})
    sched.run_slot(hour=21, seed=1)
    assert seen["goal"] == "retention"      # 21h -> rétention
    sched.run_slot(hour=7, seed=1)
    assert seen["goal"] == "engagement"
