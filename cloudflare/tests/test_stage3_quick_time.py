import asyncio
import inspect
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import core_fast_path
import quick_time
import temporal_language


class Result:
    def __init__(self, results=None, last_row_id=None):
        self.results = results or []
        self.meta = {"last_row_id": last_row_id}


class Statement:
    def __init__(self, conn, sql):
        self.conn = conn
        self.sql = sql
        self.params = ()

    def bind(self, *params):
        self.params = params
        return self

    async def first(self):
        cur = self.conn.execute(self.sql, self.params)
        return cur.fetchone()

    async def all(self):
        cur = self.conn.execute(self.sql, self.params)
        return Result(list(cur.fetchall()))

    async def run(self):
        cur = self.conn.execute(self.sql, self.params)
        self.conn.commit()
        return Result(last_row_id=cur.lastrowid)


class FakeD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                telegram_chat_id INTEGER NOT NULL UNIQUE
            );
            CREATE TABLE notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                notification_key TEXT NOT NULL,
                UNIQUE(user_id, notification_key)
            );
            """
        )
        self.conn.executemany(
            "INSERT INTO users(id,telegram_chat_id) VALUES(?,?)",
            [(10, 1010), (20, 2020)],
        )
        self.conn.commit()

    def prepare(self, sql):
        return Statement(self.conn, sql)


def test_relative_alert_examples_have_priority_over_task_semantics():
    cases = {
        "me lembra de desligar o ovo daqui a 5 minutos": ("relative_alert", 300, "desligar o ovo"),
        "tenho que ligar para alguém daqui a 10 minutos": ("relative_alert", 600, "ligar para alguém"),
        "me lembra daqui a 1 hora de tirar a roupa do varal": ("relative_alert", 3600, "tirar a roupa do varal"),
        "me avisa em 20 minutos de olhar o forno": ("relative_alert", 1200, "olhar o forno"),
    }
    for text, expected in cases.items():
        parsed = quick_time.parse_request(text)
        assert parsed["kind"] == expected[0]
        assert parsed["delay_seconds"] == expected[1]
        assert parsed["label"] == expected[2]


def test_explicit_timer_and_false_positive_contract():
    parsed = quick_time.parse_request("cronometra 30 minutos pra mim")
    assert parsed["kind"] == "timer"
    assert parsed["delay_seconds"] == 1800

    assert quick_time.parse_request("fiquei 30 minutos estudando") is None
    assert quick_time.parse_request("o filme tem 2 horas") is None
    assert quick_time.parse_request("daqui a 5 minutos talvez eu saia") is None


def test_negative_reminder_does_not_create_quick_alert():
    classified = temporal_language.classify_quick_time_intent(
        "não me lembra daqui a 5 minutos de desligar o forno"
    )
    assert classified["kind"] is None
    assert quick_time.parse_request(
        "não me lembra daqui a 5 minutos de desligar o forno"
    ) is None


def test_quick_time_has_24_hour_boundary():
    parsed = quick_time.parse_request("me lembra de olhar isso daqui a 25 horas")
    assert parsed["kind"] == "relative_alert"
    assert parsed["invalid_range"] is True


def test_core_checks_quick_time_before_compound_and_reminder_handlers():
    source = inspect.getsource(core_fast_path.handle_message)
    quick = source.index("handle_quick_time")
    compound = source.index("handle_compound_message")
    reminder = source.index("handle_colloquial_reminder")
    assert quick < compound < reminder


def test_create_timer_uses_own_table_and_keeps_users_isolated():
    async def scenario():
        db = FakeD1()
        quick_time._SCHEMA_READY = False
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        timer_a, fire_a = await quick_time.create_timer(
            db, 10, "quick_alert", "desligar o ovo", 300, now=base
        )
        timer_b, fire_b = await quick_time.create_timer(
            db, 20, "timer", "cronômetro", 600, now=base
        )
        assert timer_a != timer_b
        assert fire_a == base + timedelta(minutes=5)
        assert fire_b == base + timedelta(minutes=10)

        rows = db.conn.execute(
            "SELECT user_id,kind,label,status FROM quick_timers ORDER BY id"
        ).fetchall()
        assert [(r["user_id"], r["kind"], r["status"]) for r in rows] == [
            (10, "quick_alert", "active"),
            (20, "timer", "active"),
        ]
        tables = {
            r[0]
            for r in db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "daily_items" not in tables

    asyncio.run(scenario())


def test_user_cannot_cancel_another_users_timer():
    async def scenario():
        db = FakeD1()
        quick_time._SCHEMA_READY = False
        timer_id, _ = await quick_time.create_timer(
            db, 20, "timer", "cronômetro", 60,
            now=datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc),
        )
        row, status = await quick_time._cancel_timer(db, 10, timer_id)
        assert row is None
        assert status == "missing"
        actual = db.conn.execute(
            "SELECT status FROM quick_timers WHERE id=?", (timer_id,)
        ).fetchone()
        assert actual["status"] == "active"

    asyncio.run(scenario())


def test_due_timer_fires_once_and_marks_notification(monkeypatch):
    async def scenario():
        db = FakeD1()
        quick_time._SCHEMA_READY = False
        sent = []

        async def fake_send(token, chat, text, **kwargs):
            sent.append((chat, text))

        monkeypatch.setattr(quick_time.quality_patch, "send_message", fake_send)
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        timer_id, _ = await quick_time.create_timer(
            db, 10, "quick_alert", "desligar o ovo", 5, now=base
        )

        await quick_time.dispatch_due_quick_timers(
            db, "token", now=base + timedelta(seconds=6)
        )
        await quick_time.dispatch_due_quick_timers(
            db, "token", now=base + timedelta(seconds=20)
        )

        assert sent == [(1010, "⏰ Hora de desligar o ovo.")]
        row = db.conn.execute(
            "SELECT status,fired_at FROM quick_timers WHERE id=?", (timer_id,)
        ).fetchone()
        assert row["status"] == "fired"
        assert row["fired_at"] is not None
        log = db.conn.execute(
            "SELECT notification_key FROM notification_log WHERE user_id=10"
        ).fetchone()
        assert log["notification_key"] == f"quick_timer:{timer_id}"

    asyncio.run(scenario())


def test_next_quick_timer_returns_earliest_active_timer():
    async def scenario():
        db = FakeD1()
        quick_time._SCHEMA_READY = False
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        await quick_time.create_timer(db, 10, "timer", "longo", 600, now=base)
        await quick_time.create_timer(db, 10, "timer", "curto", 120, now=base)
        nxt = await quick_time.next_quick_timer(db, 10, now=base)
        assert nxt == base + timedelta(minutes=2)

    asyncio.run(scenario())


def test_migration_0010_is_formal_source_for_quick_timers():
    path = Path(__file__).parents[1] / "migrations" / "0010_quick_timers.sql"
    text = path.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS quick_timers" in text
    assert "FOREIGN KEY(user_id) REFERENCES users(id)" in text
    assert "idx_quick_timers_user_status_fire" in text


def test_personal_alarm_includes_quick_timer_candidates_and_dispatch():
    import personal_alarm

    source_next = inspect.getsource(personal_alarm._next_event)
    source_alarm = inspect.getsource(personal_alarm.PersonalAlarm.alarm)
    assert "next_quick_timer" in source_next
    assert "dispatch_due_quick_timers" in source_alarm
