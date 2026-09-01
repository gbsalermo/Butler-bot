import asyncio
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import course_importer
import course_operational
import course_stage4


class Result:
    def __init__(self, results=None, last_row_id=None):
        self.results = results or []
        self.meta = SimpleNamespace(last_row_id=last_row_id)
        self.last_row_id = last_row_id


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
        cur = self.conn.execute(self.sql, self.params)
        self.conn.commit()
        return Result(last_row_id=cur.lastrowid)


class FakeD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_chat_id INTEGER UNIQUE, is_owner INTEGER DEFAULT 0)"
        )
        self.conn.execute(
            "CREATE TABLE user_sessions ("
            "user_id INTEGER PRIMARY KEY,state TEXT,payload TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,"
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)"
        )
        self.conn.executemany(
            "INSERT INTO users(id,telegram_chat_id,is_owner) VALUES(?,?,?)",
            [(10, 1010, 1), (20, 2020, 0)],
        )
        self.conn.executescript(Path("migrations/0013_courses.sql").read_text(encoding="utf-8"))
        self.conn.commit()

    def prepare(self, sql):
        return Statement(self.conn, sql)


async def _state(db, uid=10):
    row = db.conn.execute("SELECT state,payload FROM user_sessions WHERE user_id=?", (uid,)).fetchone()
    if not row:
        return None, {}
    return row["state"], json.loads(row["payload"] or "{}")


SAMPLE = """\
CURSO: Java + Spring
TIPO: AUTOGERIDO
DESCRICAO: Backend moderno
[MÓDULO] Fundamentos
[CONTEÚDO] REST Controllers | aula
[MATERIAL] Slides REST | link | https://example.com/rest
[ATIVIDADE] Implementar endpoint | GET /health
[CONTEÚDO] JPA | exercício
[MÓDULO] Projeto final
[CONTEÚDO] API completa | projeto
"""


def test_parser_groups_materials_and_activities_under_the_right_content():
    plan = course_importer.parse_course_text(SAMPLE)
    assert plan["title"] == "Java + Spring"
    assert plan["mode"] == "self_paced"
    assert [m["title"] for m in plan["modules"]] == ["Fundamentos", "Projeto final"]
    rest = plan["modules"][0]["contents"][0]
    assert rest["title"] == "REST Controllers"
    assert rest["kind"] == "lesson"
    assert rest["materials"] == [
        {"title": "Slides REST", "kind": "link", "reference": "https://example.com/rest"}
    ]
    assert rest["activities"] == [
        {"title": "Implementar endpoint", "notes": "GET /health"}
    ]


def test_parser_refuses_ambiguous_unknown_lines_instead_of_guessing():
    raw = """\
CURSO: Curso ambíguo
TIPO: AUTOGERIDO
[MÓDULO] M1
Isto talvez seja uma aula sobre banco
"""
    try:
        course_importer.parse_course_text(raw)
    except course_importer.CourseImportError as exc:
        assert "não consigo associar" in str(exc)
    else:
        raise AssertionError("linha ambígua deveria bloquear importação")


def test_live_import_normalizes_schedule_and_self_paced_rejects_fixed_dates():
    live = course_importer.parse_course_text(
        "CURSO: Ao vivo\nTIPO: AO VIVO\n[MÓDULO] Semana 1\n[CONTEÚDO] Aula 1 | aula | 15/09/2026 19:30"
    )
    assert live["modules"][0]["contents"][0]["scheduled_at"] == "2026-09-15T19:30"

    try:
        course_importer.parse_course_text(
            "CURSO: Auto\nTIPO: AUTOGERIDO\n[MÓDULO] M1\n[CONTEÚDO] Aula | aula | 15/09/2026 19:30"
        )
    except course_importer.CourseImportError as exc:
        assert "AO VIVO" in str(exc)
    else:
        raise AssertionError("autogerido não deve aceitar calendário de conteúdo na importação")


def test_import_requires_preview_and_confirmation_before_persisting(monkeypatch):
    async def scenario():
        db = FakeD1()
        sent = []

        async def fake_send(token, chat_id, text, reply_markup=None):
            sent.append((text, reply_markup))
            return {"ok": True}

        monkeypatch.setattr(course_operational, "send_message", fake_send)
        course_stage4.install()

        assert await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "📥 Importar curso"},
            uid=10,
            state=None,
            payload={},
        ) is True
        state, payload = await _state(db)
        assert state == "course_import_wait"
        assert db.conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0

        assert await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": SAMPLE},
            uid=10,
            state=state,
            payload=payload,
        ) is True
        state, payload = await _state(db)
        assert state == "course_import_confirm"
        assert payload["plan"]["title"] == "Java + Spring"
        # Prévia é obrigatória: nada persistiu ainda.
        assert db.conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0
        assert any("Prévia da importação" in text for text, _ in sent)

        assert await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "✅ Confirmar importação"},
            uid=10,
            state=state,
            payload=payload,
        ) is True

        course = db.conn.execute("SELECT id,title,mode,status FROM courses").fetchone()
        assert tuple(course)[1:] == ("Java + Spring", "self_paced", "active")
        contents = db.conn.execute(
            "SELECT title,kind,status FROM course_contents ORDER BY id"
        ).fetchall()
        assert [tuple(row) for row in contents] == [
            ("REST Controllers", "lesson", "pending"),
            ("JPA", "exercise", "pending"),
            ("API completa", "project", "pending"),
        ]
        material = db.conn.execute(
            "SELECT title,kind,reference FROM course_materials"
        ).fetchone()
        assert tuple(material) == ("Slides REST", "link", "https://example.com/rest")
        activity = db.conn.execute(
            "SELECT title,status,notes FROM course_activities"
        ).fetchone()
        assert tuple(activity) == ("Implementar endpoint", "pending", "GET /health")
        assert db.conn.execute(
            "SELECT COUNT(*) FROM course_events WHERE course_id=? AND event_type='course_imported'",
            (course["id"],),
        ).fetchone()[0] == 1

    asyncio.run(scenario())


def test_invalid_import_persists_nothing(monkeypatch):
    async def scenario():
        db = FakeD1()

        async def fake_send(token, chat_id, text, reply_markup=None):
            return {"ok": True}

        monkeypatch.setattr(course_operational, "send_message", fake_send)
        await course_stage4._start_import(db, "token", 1010, 10)
        state, payload = await _state(db)
        await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "CURSO: X\n[MÓDULO] M\nlinha solta"},
            uid=10,
            state=state,
            payload=payload,
        )
        assert db.conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0
        assert (await _state(db))[0] == "course_import_wait"

    asyncio.run(scenario())
