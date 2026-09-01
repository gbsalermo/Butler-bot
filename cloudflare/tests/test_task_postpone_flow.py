import asyncio
from datetime import date, datetime

import nlu
import runtime_guard
import short_context
import task_context_patch


class _Statement:
    def __init__(self, db, sql):
        self.db = db
        self.sql = sql
        self.values = ()

    def bind(self, *values):
        self.values = values
        return self

    async def run(self):
        self.db.executed.append((self.sql, self.values))

    async def first(self):
        self.db.reads.append((self.sql, self.values))
        if "FROM daily_items" in self.sql and self.values:
            task_id = int(self.values[0])
            return {"id": task_id, "title": f"task {task_id}", "kind": "tarefa", "status": "pendente"}
        return None


class _DB:
    def __init__(self):
        self.executed = []
        self.reads = []

    def prepare(self, sql):
        return _Statement(self, sql)


def test_postpone_date_keeps_task_selected_in_previous_turn(monkeypatch):
    db = _DB()
    sent = []
    cleared = []

    async def fake_state(_db, _uid):
        return "guard_task_postpone_when", {"id": 42, "title": "estudar física"}

    async def fake_send(_token, _chat, text, keyboard):
        sent.append((text, keyboard))

    async def fake_clear(_db, uid):
        cleared.append(uid)

    async def fail_base_handler(*_args, **_kwargs):
        raise AssertionError("o handler base não deve tentar escolher a tarefa novamente")

    monkeypatch.setattr(runtime_guard, "_state", fake_state)
    monkeypatch.setattr(runtime_guard, "_send", fake_send)
    monkeypatch.setattr(runtime_guard, "_clear", fake_clear)
    monkeypatch.setattr(runtime_guard, "_now", lambda: datetime(2026, 8, 31, 22, 26))
    monkeypatch.setattr(task_context_patch, "_BASE_RUNTIME_HANDLE_STATE", fail_base_handler)
    monkeypatch.setattr(nlu, "parse_date", lambda _text, _base: date(2026, 9, 1))
    monkeypatch.setattr(nlu, "parse_time", lambda _text: "08:00")
    monkeypatch.setattr(nlu, "validate_future", lambda _date, _time, _now: (True, None))

    handled = asyncio.run(
        task_context_patch._handle_runtime_state(
            db,
            "token",
            123,
            7,
            "Amanhã às 8h",
        )
    )

    assert handled is True
    assert len(db.executed) == 1
    _, values = db.executed[0]
    assert values == ("2026-09-01", "08:00", "2026-09-01 08:00", 42, 7)
    assert cleared == [7]
    assert sent
    assert "estudar física adiada para 01/09 às 08:00" in sent[-1][0]
    assert "Qual tarefa?" not in sent[-1][0]


def test_numeric_task_position_uses_the_list_the_user_actually_saw(monkeypatch):
    db = _DB()

    async def fake_latest(_db, _uid):
        return {
            "kind": "tarefa",
            "id": 42,
            "candidate_ids": [42, 99],
        }

    async def changed_visible_order(_db, _uid):
        # Simula o banco mudando entre a listagem e a resposta do usuário.
        return [
            {"id": 99, "title": "segunda agora", "status": "pendente"},
            {"id": 42, "title": "primeira que foi exibida", "status": "pendente"},
        ]

    monkeypatch.setattr(short_context, "latest", fake_latest)
    monkeypatch.setattr(task_context_patch, "_visible_tasks", changed_visible_order)

    task = asyncio.run(task_context_patch._find_task(db, 7, "1"))

    assert task["id"] == 42
    assert db.reads
    _, values = db.reads[-1]
    assert values == (42, 7)
