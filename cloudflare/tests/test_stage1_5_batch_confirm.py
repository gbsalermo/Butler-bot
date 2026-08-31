import asyncio
from datetime import datetime, timedelta

import compound_router


def _now():
    return datetime(2026, 8, 31, 19, 0, tzinfo=compound_router.LOCAL_TZ)


def test_complete_task_and_appointment_can_be_prevalidated_as_batch():
    analysis = compound_router.analyze_compound(
        "tenho que pagar o boleto amanhã e tenho dentista sexta às 15h"
    )
    plan = compound_router.build_batch_plan(analysis, now=_now())

    assert plan is not None
    assert [item["family"] for item in plan] == ["create_task", "create_appointment"]
    assert plan[0]["title"] == "pagar o boleto"
    assert plan[0]["due_date"] == "2026-09-01"
    assert plan[1]["title"] == "dentista"
    assert plan[1]["due_date"] == "2026-09-04"
    assert plan[1]["due_time"] == "15:00"


def test_incomplete_action_never_offers_atomic_registration():
    analysis = compound_router.analyze_compound(
        "tenho que pagar o boleto e tenho dentista sexta às 15h"
    )
    assert analysis["is_compound_action"] is True
    assert compound_router.build_batch_plan(analysis, now=_now()) is None


def test_reminder_requires_exact_time_before_entering_batch():
    complete = compound_router.analyze_compound(
        "me lembra de enviar o documento amanhã às 9h e tenho que pagar a conta sexta"
    )
    plan = compound_router.build_batch_plan(complete, now=_now())
    assert plan is not None
    assert plan[0]["family"] == "reminder"
    assert plan[0]["details"] == "simple_reminder"
    assert plan[0]["due_time"] == "09:00"

    incomplete = compound_router.analyze_compound(
        "me lembra de enviar o documento amanhã e tenho que pagar a conta sexta"
    )
    assert compound_router.build_batch_plan(incomplete, now=_now()) is None


def test_context_or_alternative_never_becomes_batch():
    cause = compound_router.analyze_compound(
        "tenho dentista amanhã porque tenho que buscar um documento"
    )
    assert compound_router.build_batch_plan(cause, now=_now()) is None

    alternative = compound_router.analyze_compound(
        "tenho dentista amanhã ou tenho reunião sexta às 15h"
    )
    assert compound_router.build_batch_plan(alternative, now=_now()) is None


def test_batch_confirmation_expires_after_short_window():
    fresh = {"prepared_at": _now().isoformat()}
    stale = {"prepared_at": (_now() - timedelta(minutes=11)).isoformat()}
    assert compound_router._batch_is_fresh(fresh, now=_now()) is True
    assert compound_router._batch_is_fresh(stale, now=_now()) is False


class _Result:
    def __init__(self, rows):
        self.results = rows


class _Stmt:
    def __init__(self, db, sql):
        self.db = db
        self.sql = " ".join(sql.split())
        self.args = ()

    def bind(self, *args):
        self.args = args
        return self

    async def all(self):
        assert self.sql.startswith("INSERT INTO daily_items")
        self.db.insert_calls += 1
        assert self.db.insert_calls == 1
        rows = []
        for offset in range(0, len(self.args), 6):
            uid, kind, title, details, due_date, due_time = self.args[offset:offset + 6]
            item_id = len(self.db.items) + 1
            self.db.items.append(
                {
                    "id": item_id,
                    "user_id": uid,
                    "kind": kind,
                    "title": title,
                    "details": details,
                    "due_date": due_date,
                    "due_time": due_time,
                }
            )
            rows.append({"id": item_id})
        return _Result(rows)


class _DB:
    def __init__(self):
        self.items = []
        self.insert_calls = 0

    def prepare(self, sql):
        return _Stmt(self, sql)


def test_confirmation_persists_whole_batch_with_single_insert(monkeypatch):
    plans = [
        {
            "family": "create_task",
            "kind": "tarefa",
            "title": "pagar boleto",
            "details": None,
            "due_date": "2026-09-01",
            "due_time": None,
        },
        {
            "family": "create_appointment",
            "kind": "compromisso",
            "title": "dentista",
            "details": None,
            "due_date": "2026-09-04",
            "due_time": "15:00",
        },
    ]
    cleared = []
    remembered = []
    sent = []

    async def fake_uid(_db, _chat_id):
        return 7

    async def fake_get_state(_db, uid):
        assert uid == 7
        return compound_router.BATCH_STATE, {
            "plans": plans,
            "prepared_at": _now().isoformat(),
        }

    async def fake_clear(_db, uid):
        cleared.append(uid)

    async def fake_remember(_db, uid, kind, ids, source=None):
        remembered.append((uid, kind, ids, source))

    async def fake_send(_token, chat_id, text, **_kwargs):
        sent.append((chat_id, text))

    monkeypatch.setattr(compound_router, "_uid", fake_uid)
    monkeypatch.setattr(compound_router.app, "get_state", fake_get_state)
    monkeypatch.setattr(compound_router.app, "clear_state", fake_clear)
    monkeypatch.setattr(compound_router.short_context, "remember_list", fake_remember)
    monkeypatch.setattr(compound_router, "send_message", fake_send)
    monkeypatch.setattr(compound_router, "_now", _now)

    db = _DB()
    handled = asyncio.run(compound_router._confirm_batch(db, "token", 100))

    assert handled is True
    assert db.insert_calls == 1
    assert len(db.items) == 2
    assert cleared == [7]
    assert remembered == [(7, "daily_item", [1, 2], "compound_created")]
    assert sent and "Registrei 2 ações" in sent[-1][1]


def test_plain_message_still_requires_zero_db_access():
    class _NoDB:
        def prepare(self, sql):
            raise AssertionError(f"mensagem comum não deveria tocar D1: {sql}")

    handled = asyncio.run(
        compound_router.handle_message(
            _NoDB(),
            "token",
            {"chat": {"id": 100}, "text": "como está meu dia?"},
        )
    )
    assert handled is False
