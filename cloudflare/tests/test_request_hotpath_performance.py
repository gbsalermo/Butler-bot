import asyncio
import json

import app
import goal_operational
import operational_menu
import performance_patch
import production_usability_patch
import runtime_guard


class _Result:
    def __init__(self, rows=None):
        self.results = rows or []


class _Stmt:
    def __init__(self, db, sql):
        self.db = db
        self.sql = " ".join(sql.split())
        self.args = ()
        self.db.sql.append(self.sql)

    def bind(self, *args):
        self.args = args
        return self

    async def first(self):
        if "FROM users WHERE telegram_chat_id=?" in self.sql:
            return {"id": 1, "preferred_name": "Chefe", "is_owner": 1}
        if "FROM user_sessions WHERE user_id=?" in self.sql:
            return {"state": self.db.state, "payload": json.dumps(self.db.payload)}
        return None

    async def run(self):
        if self.sql.startswith("INSERT INTO user_sessions"):
            _uid, state, payload = self.args
            self.db.state = state
            self.db.payload = json.loads(payload or "{}")
        return _Result([])

    async def all(self):
        return _Result([])


class _DB:
    def __init__(self, state=None, payload=None):
        self.sql = []
        self.state = state
        self.payload = payload or {}

    def prepare(self, sql):
        return _Stmt(self, sql)

    def count(self, fragment):
        return sum(fragment in sql for sql in self.sql)


def test_uid_and_state_are_shared_between_hot_handlers():
    async def scenario():
        db = _DB()
        performance_patch.reset_request_cache()

        uid_a = await production_usability_patch._resolve_user(db, 100)
        state_a = await app.get_state(db, uid_a)

        uid_b = await operational_menu._uid(db, 100)
        state_b = await runtime_guard._state(db, uid_b)

        uid_c = await goal_operational._uid(db, 100)
        return db, (uid_a, uid_b, uid_c), state_a, state_b

    db, uids, state_a, state_b = asyncio.run(scenario())
    assert uids == (1, 1, 1)
    assert state_a == (None, {})
    assert state_b == (None, {})
    assert db.count("FROM users WHERE telegram_chat_id=?") == 1
    assert db.count("FROM user_sessions WHERE user_id=?") == 1


def test_state_write_refreshes_cache_without_second_select():
    async def scenario():
        db = _DB()
        performance_patch.reset_request_cache()
        before = await app.get_state(db, 1)
        await app.set_state(db, 1, "appointment_title", {"source": "test"})
        after = await runtime_guard._state(db, 1)
        return db, before, after

    db, before, after = asyncio.run(scenario())
    assert before == (None, {})
    assert after == ("appointment_title", {"source": "test"})
    assert db.count("FROM user_sessions WHERE user_id=?") == 1


def test_irrelevant_message_does_not_touch_later_schema(monkeypatch):
    async def fail_schema(_db):
        raise AssertionError("schema de Ler/Ver Depois não pertence ao caminho comum")

    monkeypatch.setattr(production_usability_patch, "ensure_schema", fail_schema)

    async def scenario():
        db = _DB()
        handled = await production_usability_patch.handle_message(
            db,
            "token",
            {"chat": {"id": 100}, "text": "me lembra amanhã às 10h de levar o documento"},
        )
        return handled, db

    handled, db = asyncio.run(scenario())
    assert handled is False
    assert not any("CREATE TABLE" in sql or "CREATE INDEX" in sql for sql in db.sql)


def test_non_goal_text_skips_all_goal_handlers(monkeypatch):
    async def must_not_run(*_args, **_kwargs):
        raise AssertionError("handler de metas não deveria rodar fora do domínio")

    monkeypatch.setattr(operational_menu.goal_natural_patch, "handle_message", must_not_run)
    monkeypatch.setattr(operational_menu.goal_deadline_patch, "handle_message", must_not_run)
    monkeypatch.setattr(operational_menu.goal_polish, "handle_message", must_not_run)
    monkeypatch.setattr(operational_menu.goal_operational, "handle_message", must_not_run)

    async def scenario():
        db = _DB()
        performance_patch.reset_request_cache()
        handled = await operational_menu.handle_message(
            db,
            "token",
            {"chat": {"id": 100}, "text": "me lembra amanhã às 10h de levar o documento"},
        )
        return handled

    assert asyncio.run(scenario()) is False


def test_goal_state_still_reaches_goal_handlers(monkeypatch):
    calls = []

    async def natural(*_args, **_kwargs):
        calls.append("natural")
        return True

    monkeypatch.setattr(operational_menu.goal_natural_patch, "handle_message", natural)

    async def scenario():
        db = _DB(state="goal_relative_weight_start", payload={"delta": 10, "name": "Perder 10 kg"})
        performance_patch.reset_request_cache()
        handled = await operational_menu.handle_message(
            db,
            "token",
            {"chat": {"id": 100}, "text": "90 kg"},
        )
        return handled

    assert asyncio.run(scenario()) is True
    assert calls == ["natural"]
