import asyncio

import routine_integration
import runtime_guard
from core_fast_path import is_core_candidate
from routine_natural_fastpath import _extract_name, _looks_like_create


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
        if "FROM user_sessions" in self.sql:
            session = self.db.sessions.get(int(self.args[0]))
            return dict(session) if session else None
        if "FROM routines WHERE id=?" in self.sql:
            rid = int(self.args[0])
            uid = int(self.args[1]) if len(self.args) > 1 else None
            for routine in self.db.routines:
                if routine["id"] == rid and (uid is None or routine["user_id"] == uid):
                    return dict(routine)
            return None
        if "FROM goals" in self.sql:
            return None
        return None

    async def all(self):
        if "FROM users u" in self.sql:
            return _Result(self.db.users)
        if "FROM routines" in self.sql:
            uid = int(self.args[0]) if self.args else None
            rows = [r for r in self.db.routines if uid is None or r["user_id"] == uid]
            return _Result([dict(row) for row in rows])
        return _Result([])

    async def run(self):
        if "INSERT INTO user_sessions" in self.sql:
            uid, state, payload = self.args[:3]
            self.db.sessions[int(uid)] = {"state": state, "payload": payload}
            return None
        if "INSERT INTO routines" in self.sql:
            uid, name, category, time_hhmm, weekdays = self.args[:5]
            self.db.routines.append(
                {
                    "id": len(self.db.routines) + 1,
                    "user_id": int(uid),
                    "name": name,
                    "category": category,
                    "time_hhmm": time_hhmm,
                    "weekdays": weekdays,
                    "active": 1,
                }
            )
            return None
        if "INSERT INTO routine_logs" in self.sql:
            rid, log_date = self.args[:2]
            self.db.routine_logs[(int(rid), log_date)] = "feito"
            return None
        return None


class _DB:
    def __init__(self):
        self.sessions = {}
        self.routines = []
        self.routine_logs = {}
        self.users = [
            {"id": 1, "telegram_chat_id": 12345, "day_off": 0},
        ]

    def prepare(self, sql):
        return _Stmt(self, sql)


def test_criar_outra_rotina_entra_no_fastpath():
    text = "cria outra rotina de Academia segunda, quarta e sexta às 19h"
    assert _looks_like_create(text)
    assert _extract_name(text) == "Academia"
    assert is_core_candidate(text)


def test_adicionar_mais_uma_rotina_entra_no_fastpath():
    text = "adiciona mais uma rotina Curso DIO todos os dias 20h"
    assert _looks_like_create(text)
    assert _extract_name(text) == "Curso DIO"
    assert is_core_candidate(text)


def test_sequencia_natural_de_varias_rotinas_nao_perde_o_segundo_pedido():
    requests = [
        ("cria uma rotina de Estudar inglês terça e quinta às 18h", "Estudar inglês"),
        ("cria outra rotina de Academia segunda, quarta e sexta às 19h", "Academia"),
        ("adiciona mais uma rotina Curso DIO todos os dias 20h", "Curso DIO"),
    ]

    for text, expected_name in requests:
        assert _looks_like_create(text)
        assert _extract_name(text) == expected_name
        assert is_core_candidate(text)


def test_fluxo_guiado_persiste_tres_rotinas_do_mesmo_usuario(monkeypatch):
    sent = []

    async def fake_send(_token, _chat, text, **_kwargs):
        sent.append(text)

    monkeypatch.setattr(runtime_guard, "send_message", fake_send)

    async def scenario():
        db = _DB()
        uid = 1
        chat = 12345
        entries = [
            ("Estudar inglês", "Inglês", "18h terça quinta"),
            ("Academia", "Musculação", "19h segunda quarta sexta"),
            ("Curso DIO", "Programação", "20h todos os dias"),
        ]
        for name, category, when in entries:
            await runtime_guard._set_state(db, uid, "guard_routine_name", {})
            assert await runtime_guard._handle_state(db, "token", chat, uid, name)
            assert await runtime_guard._handle_state(db, "token", chat, uid, category)
            assert await runtime_guard._handle_state(db, "token", chat, uid, when)

        listing = await runtime_guard._routine_list(db, uid)
        return db, listing

    db, listing = asyncio.run(scenario())
    assert [r["name"] for r in db.routines] == ["Estudar inglês", "Academia", "Curso DIO"]
    assert all(r["user_id"] == 1 for r in db.routines)
    assert "Estudar inglês" in listing
    assert "Academia" in listing
    assert "Curso DIO" in listing


def test_concluir_uma_rotina_nao_conclui_as_demais(monkeypatch):
    async def fake_send(_token, _chat, _text, **_kwargs):
        return None

    monkeypatch.setattr(runtime_guard, "send_message", fake_send)

    async def scenario():
        db = _DB()
        db.routines = [
            {"id": 1, "user_id": 1, "name": "Inglês", "category": "Estudos", "time_hhmm": "18:00", "weekdays": "terça", "active": 1},
            {"id": 2, "user_id": 1, "name": "Academia", "category": "Musculação", "time_hhmm": "19:00", "weekdays": "terça", "active": 1},
            {"id": 3, "user_id": 1, "name": "Curso DIO", "category": "Programação", "time_hhmm": "20:00", "weekdays": "terça", "active": 1},
        ]
        await runtime_guard._set_state(db, 1, "guard_routine_done", {})
        assert await runtime_guard._handle_state(db, "token", 12345, 1, "#2")
        return db

    db = asyncio.run(scenario())
    assert len(db.routine_logs) == 1
    assert next(iter(db.routine_logs))[0] == 2


def test_scheduler_percorre_cada_rotina_independentemente(monkeypatch):
    calls = []

    async def fake_dispatch(_db, _token, uid, chat, routine, _today, _now):
        calls.append((uid, chat, routine["id"]))

    monkeypatch.setattr(routine_integration, "_dispatch_one_routine", fake_dispatch)

    async def scenario():
        db = _DB()
        db.routines = [
            {"id": 1, "user_id": 1, "name": "Inglês", "category": "Estudos", "time_hhmm": "18:00", "weekdays": "todos os dias", "active": 1},
            {"id": 2, "user_id": 1, "name": "Academia", "category": "Musculação", "time_hhmm": "19:00", "weekdays": "todos os dias", "active": 1},
            {"id": 3, "user_id": 1, "name": "Curso DIO", "category": "Programação", "time_hhmm": "20:00", "weekdays": "todos os dias", "active": 1},
        ]
        await routine_integration._routine_reminders(db, "token")

    asyncio.run(scenario())
    assert calls == [(1, 12345, 1), (1, 12345, 2), (1, 12345, 3)]
