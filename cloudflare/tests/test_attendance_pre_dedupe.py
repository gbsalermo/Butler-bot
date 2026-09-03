import asyncio
from datetime import datetime, timezone

import attendance_production_fix as attendance_fix


class _Statement:
    def __init__(self, db, sql):
        self.db = db
        self.sql = sql
        self.params = ()

    def bind(self, *params):
        self.params = params
        return self

    async def first(self):
        if "SELECT id FROM notification_log" in self.sql:
            uid, key = self.params
            return {"id": 1} if (int(uid), key) in self.db.sent else None
        raise AssertionError(f"SQL inesperado em first(): {self.sql}")

    async def run(self):
        if "INSERT OR IGNORE INTO notification_log" in self.sql:
            uid, key = self.params
            self.db.sent.add((int(uid), key))
            return None
        raise AssertionError(f"SQL inesperado em run(): {self.sql}")


class _DB:
    def __init__(self, sent=None):
        self.sent = set(sent or ())

    def prepare(self, sql):
        return _Statement(self, sql)


def _session():
    return {
        "id": 42,
        "name": "Princípios de Eletrônica Analógica",
        "start_time": "08:00",
        "end_time": "10:00",
        "location": "PAV I, Sala 104",
    }


def test_pre_class_marks_reliable_and_legacy_keys(monkeypatch):
    db = _DB()
    sent_messages = []

    async def fake_send_message(token, chat_id, text, **kwargs):
        sent_messages.append((token, chat_id, text, kwargs))
        return {"ok": True}

    monkeypatch.setattr(attendance_fix, "send_message", fake_send_message)

    now = datetime(2026, 9, 3, 7, 50, tzinfo=timezone.utc)
    start = datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc)

    asyncio.run(
        attendance_fix._dispatch_pre(
            db,
            "token",
            _session(),
            7,
            123,
            42,
            "2026-09-03",
            now,
            start,
            "10:00",
        )
    )

    assert len(sent_messages) == 1
    assert (7, "attendance:pre:2026-09-03:42") in db.sent
    assert (
        7,
        "class:2026-09-03:Princípios de Eletrônica Analógica:08:00",
    ) in db.sent


def test_pre_class_skips_when_legacy_scheduler_already_sent(monkeypatch):
    legacy_key = "class:2026-09-03:Princípios de Eletrônica Analógica:08:00"
    db = _DB({(7, legacy_key)})

    async def must_not_send(*_args, **_kwargs):
        raise AssertionError("o aviso confiável não pode duplicar o aviso legado")

    monkeypatch.setattr(attendance_fix, "send_message", must_not_send)

    now = datetime(2026, 9, 3, 7, 50, tzinfo=timezone.utc)
    start = datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc)

    asyncio.run(
        attendance_fix._dispatch_pre(
            db,
            "token",
            _session(),
            7,
            123,
            42,
            "2026-09-03",
            now,
            start,
            "10:00",
        )
    )

    assert (7, "attendance:pre:2026-09-03:42") not in db.sent
