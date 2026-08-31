import asyncio
from datetime import datetime, timedelta

import entry
import personal_alarm
import worker


class _Result:
    def __init__(self, rows=None):
        self.results = rows or []


class _Stmt:
    def __init__(self, db, sql):
        self.db = db
        self.sql = sql
        self.args = ()

    def bind(self, *args):
        self.args = args
        return self

    async def first(self):
        if "assistant_state" in self.sql:
            return {"day_off": self.db.day_off}
        if "notification_log" in self.sql:
            return None
        return None

    async def all(self):
        if "FROM daily_items" in self.sql:
            return _Result(self.db.items)
        if "FROM routines" in self.sql:
            return _Result(self.db.routines)
        return _Result([])


class _DB:
    def __init__(self, *, day_off=0, items=None, routines=None):
        self.day_off = day_off
        self.items = items or []
        self.routines = routines or []

    def prepare(self, sql):
        return _Stmt(self, sql)


def _local(year, month, day, hour, minute=0):
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        tzinfo=personal_alarm.LOCAL_TZ,
    )


def test_appointment_alarm_is_scheduled_five_minutes_before():
    item = {
        "id": 1,
        "kind": "compromisso",
        "due_date": "2026-08-30",
        "due_time": "18:00",
        "details": "",
    }
    desired, logical_kind = personal_alarm._item_desired(item)
    assert logical_kind == "compromisso"
    assert desired == _local(2026, 8, 30, 17, 55)


def test_task_can_recover_late_on_same_day_but_simple_reminder_cannot():
    now = _local(2026, 8, 30, 17, 30)
    old = _local(2026, 8, 30, 17, 0)

    task = personal_alarm._recoverable_candidate(now, old, "tarefa")
    simple = personal_alarm._recoverable_candidate(now, old, "lembrete")

    assert task == now + timedelta(seconds=1)
    assert simple is None


def test_alarm_stays_armed_with_weekly_summary_when_it_is_the_next_event():
    async def scenario():
        db = _DB()
        now = _local(2026, 8, 30, 13, 0)  # domingo
        return await personal_alarm._next_event(db, 1, now=now)

    next_event = asyncio.run(scenario())
    assert next_event == _local(2026, 8, 30, 20, 0)


def test_after_weekly_window_next_alarm_is_next_morning():
    async def scenario():
        db = _DB()
        now = _local(2026, 8, 30, 21, 5)
        return await personal_alarm._next_event(db, 1, now=now)

    next_event = asyncio.run(scenario())
    assert next_event == _local(2026, 8, 31, 7, 0)


def test_day_off_skips_today_but_keeps_tomorrow_alarm_alive():
    async def scenario():
        db = _DB(day_off=1)
        now = _local(2026, 8, 30, 6, 0)
        return await personal_alarm._next_event(db, 1, now=now)

    next_event = asyncio.run(scenario())
    assert next_event == _local(2026, 8, 31, 7, 0)


def test_post_webhook_rearms_persistent_alarms_without_blocking_response(monkeypatch):
    calls = []

    async def fake_core_fetch(self, request):
        calls.append("core")
        return "ok"

    async def fake_attendance(env):
        calls.append("attendance")

    async def fake_personal(env):
        calls.append("personal")

    monkeypatch.setattr(entry.Default, "fetch", fake_core_fetch)
    monkeypatch.setattr(worker, "sync_attendance_alarms", fake_attendance)
    monkeypatch.setattr(worker, "sync_personal_alarms", fake_personal)

    class _Ctx:
        def __init__(self):
            self.tasks = []

        def waitUntil(self, awaitable):
            self.tasks.append(awaitable)

    async def scenario():
        instance = worker.Default()
        instance.env = object()
        instance.ctx = _Ctx()
        request = type(
            "Request",
            (),
            {"method": "POST", "url": "https://butler/telegram/webhook"},
        )()
        response = await instance.fetch(request)
        calls_before_background = list(calls)
        await asyncio.gather(*instance.ctx.tasks)
        return response, calls_before_background, list(calls)

    response, before, after = asyncio.run(scenario())
    assert response == "ok"
    assert before == ["core"]
    assert after == ["core", "attendance", "personal"]


def test_non_webhook_post_does_not_start_global_alarm_sync(monkeypatch):
    calls = []

    async def fake_core_fetch(self, request):
        calls.append("core")
        return "ok"

    monkeypatch.setattr(entry.Default, "fetch", fake_core_fetch)

    class _Ctx:
        def __init__(self):
            self.tasks = []

        def waitUntil(self, awaitable):
            self.tasks.append(awaitable)

    async def scenario():
        instance = worker.Default()
        instance.env = object()
        instance.ctx = _Ctx()
        request = type("Request", (), {"method": "POST", "url": "https://butler/other"})()
        response = await instance.fetch(request)
        return response, instance.ctx.tasks

    response, tasks = asyncio.run(scenario())
    assert response == "ok"
    assert tasks == []
    assert calls == ["core"]
