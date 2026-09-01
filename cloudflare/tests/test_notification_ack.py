import asyncio
import inspect
import sqlite3

import core_fast_path
import notification_ack


class Result:
    def __init__(self, results=None):
        self.results = results or []


class Statement:
    def __init__(self, conn, sql):
        self.conn = conn
        self.sql = sql
        self.params = ()

    def bind(self, *params):
        self.params = params
        return self

    async def first(self):
        return self.conn.execute(self.sql, self.params).fetchone()

    async def all(self):
        return Result(list(self.conn.execute(self.sql, self.params).fetchall()))

    async def run(self):
        self.conn.execute(self.sql, self.params)
        self.conn.commit()
        return Result()


class FakeD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.query_count = 0
        self.conn.executescript("""
            CREATE TABLE users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_chat_id INTEGER UNIQUE
            );
            CREATE TABLE natural_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                target_id INTEGER,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO users(telegram_chat_id) VALUES(123);
        """)

    def prepare(self, sql):
        self.query_count += 1
        return Statement(self.conn, sql)


def test_ack_phrases_cover_requested_natural_replies():
    for text in ("Valeu", "desliguei", "fechado", "já foi", "terminei", "feito"):
        assert notification_ack.ack_kind(text) in {"thanks", "done"}


def test_non_ack_message_does_not_touch_database():
    async def scenario():
        db = FakeD1()
        handled = await notification_ack.handle_message(
            db, "token", {"chat": {"id": 123}, "text": "qual o tempo amanhã?"}
        )
        assert handled is False
        assert db.query_count == 0

    asyncio.run(scenario())


def test_recent_alert_can_receive_one_optional_ack(monkeypatch):
    async def scenario():
        db = FakeD1()
        sent = []

        async def fake_send(token, chat_id, text, **kwargs):
            sent.append(text)

        async def fake_uid(db_arg, chat_id):
            return 1

        monkeypatch.setattr(notification_ack, "send_message", fake_send)
        monkeypatch.setattr(notification_ack.runtime_guard, "_uid", fake_uid)

        await notification_ack.remember_notification(
            db, 1, "quick_alert", 77, "desligar o ovo"
        )
        handled = await notification_ack.handle_message(
            db, "token", {"chat": {"id": 123}, "text": "desliguei"}
        )
        assert handled is True
        assert sent and any(x in sent[0] for x in ("resolvido", "Fechado", "Perfeito"))

        ack = db.conn.execute(
            "SELECT event_type,target_id FROM natural_events "
            "WHERE event_type='notification_ack'"
        ).fetchone()
        assert ack is not None

        # O mesmo aviso já foi reconhecido; responder de novo não reabre contexto.
        handled_again = await notification_ack.handle_message(
            db, "token", {"chat": {"id": 123}, "text": "valeu"}
        )
        assert handled_again is False
        assert len(sent) == 1

    asyncio.run(scenario())


def test_old_alert_is_not_used_as_conversation_context(monkeypatch):
    async def scenario():
        db = FakeD1()
        async def fake_uid(db_arg, chat_id):
            return 1
        async def fake_send(*args, **kwargs):
            raise AssertionError("old alert must not answer")
        monkeypatch.setattr(notification_ack.runtime_guard, "_uid", fake_uid)
        monkeypatch.setattr(notification_ack, "send_message", fake_send)

        await db.prepare(
            "INSERT INTO natural_events(user_id,event_type,target_id,detail,created_at) "
            "VALUES(1,'notification_sent',9,'{}',datetime('now','-30 minutes'))"
        ).run()
        handled = await notification_ack.handle_message(
            db, "token", {"chat": {"id": 123}, "text": "valeu"}
        )
        assert handled is False

    asyncio.run(scenario())


def test_study_mode_keeps_precedence_over_social_ack():
    source = inspect.getsource(core_fast_path.handle_message)
    assert source.index("handle_study_mode") < source.index("handle_notification_ack")
