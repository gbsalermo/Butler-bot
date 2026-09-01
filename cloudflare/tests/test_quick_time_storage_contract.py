import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone

import quick_time


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
            INSERT INTO users(id,telegram_chat_id) VALUES(10,1010);
            """
        )
        self.conn.commit()

    def prepare(self, sql):
        return Statement(self.conn, sql)


def test_exact_user_phrase_is_relative_alert():
    parsed = quick_time.parse_request("Me lembra de desligar o ovo em 5 minutos")
    assert parsed == {
        "kind": "relative_alert",
        "delay_seconds": 300,
        "label": "desligar o ovo",
        "invalid_range": False,
    }


def test_relative_alert_is_normalized_to_quick_alert_before_insert():
    async def scenario():
        db = FakeD1()
        quick_time._SCHEMA_READY = False
        timer_id, _ = await quick_time.create_timer(
            db,
            10,
            "relative_alert",
            "desligar o ovo",
            300,
            now=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
        )
        row = db.conn.execute(
            "SELECT id,kind,label,delay_seconds,status FROM quick_timers WHERE id=?",
            (timer_id,),
        ).fetchone()
        assert row["kind"] == "quick_alert"
        assert row["label"] == "desligar o ovo"
        assert row["delay_seconds"] == 300
        assert row["status"] == "active"

    asyncio.run(scenario())


def test_exact_user_phrase_creates_and_confirms_without_check_constraint(monkeypatch):
    async def scenario():
        db = FakeD1()
        quick_time._SCHEMA_READY = False
        sent = []

        async def fake_send(token, chat_id, text, **kwargs):
            sent.append((chat_id, text))

        monkeypatch.setattr(quick_time, "send_message", fake_send)
        consumed = await quick_time.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "Me lembra de desligar o ovo em 5 minutos"},
        )
        assert consumed is True
        row = db.conn.execute(
            "SELECT kind,label,delay_seconds,status FROM quick_timers ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row["kind"] == "quick_alert"
        assert row["label"] == "desligar o ovo"
        assert row["delay_seconds"] == 300
        assert row["status"] == "active"
        assert len(sent) == 1
        assert "Em 5 minutos" in sent[0][1]
        assert "desligar o ovo" in sent[0][1]

    asyncio.run(scenario())


def test_stored_quick_alert_is_delivered_once(monkeypatch):
    async def scenario():
        db = FakeD1()
        quick_time._SCHEMA_READY = False
        delivered = []
        base = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
        timer_id, fire_at = await quick_time.create_timer(
            db, 10, "relative_alert", "desligar o ovo", 300, now=base
        )

        async def fake_delivery(token, chat_id, text, **kwargs):
            delivered.append((chat_id, text))

        monkeypatch.setattr(quick_time.quality_patch, "send_message", fake_delivery)
        await quick_time.dispatch_due_quick_timers(
            db, "token", user_id=10, now=fire_at + timedelta(seconds=1)
        )
        await quick_time.dispatch_due_quick_timers(
            db, "token", user_id=10, now=fire_at + timedelta(seconds=2)
        )

        assert delivered == [(1010, "⏰ Hora de desligar o ovo.")]
        row = db.conn.execute(
            "SELECT status FROM quick_timers WHERE id=?", (timer_id,)
        ).fetchone()
        assert row["status"] == "fired"

    asyncio.run(scenario())


def test_explicit_timer_storage_kind_remains_timer():
    async def scenario():
        db = FakeD1()
        quick_time._SCHEMA_READY = False
        timer_id, _ = await quick_time.create_timer(
            db,
            10,
            "timer",
            "cronômetro",
            120,
            now=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
        )
        row = db.conn.execute(
            "SELECT kind FROM quick_timers WHERE id=?", (timer_id,)
        ).fetchone()
        assert row["kind"] == "timer"

    asyncio.run(scenario())
