import asyncio
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import course_domain
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


async def _fixture_course(db, *, mode="self_paced"):
    course_id = await course_domain.create_course(db, 10, "Java + Spring", mode=mode)
    module_id = await course_domain.add_module(db, 10, course_id, "Fundamentos")
    first = await course_domain.add_content(db, 10, course_id, module_id, "REST")
    second = await course_domain.add_content(db, 10, course_id, module_id, "JPA")
    return course_id, module_id, first, second


def test_continue_is_read_only_and_progress_is_explicit(monkeypatch):
    async def scenario():
        db = FakeD1()
        sent = []

        async def fake_send(token, chat_id, text, reply_markup=None):
            sent.append((text, reply_markup))
            return {"ok": True}

        monkeypatch.setattr(course_operational, "send_message", fake_send)
        course_stage4.install()
        course_id, module_id, first, second = await _fixture_course(db)

        await course_stage4._show_course(db, "token", 1010, 10, course_id)
        state, payload = await _state(db)
        assert state == "course_view"

        handled = await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "▶️ Continuar curso"},
            uid=10,
            state=state,
            payload=payload,
        )
        assert handled is True
        assert db.conn.execute("SELECT status FROM course_contents WHERE id=?", (first,)).fetchone()[0] == "pending"
        state, payload = await _state(db)
        assert state == "course_content_view"
        assert payload["content_id"] == first

        await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "✅ Concluir conteúdo"},
            uid=10,
            state=state,
            payload=payload,
        )
        assert db.conn.execute("SELECT status FROM course_contents WHERE id=?", (first,)).fetchone()[0] == "completed"
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()[0] == "active"

        await course_stage4._show_course(db, "token", 1010, 10, course_id)
        state, payload = await _state(db)
        await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "▶️ Continuar curso"},
            uid=10,
            state=state,
            payload=payload,
        )
        state, payload = await _state(db)
        assert payload["content_id"] == second

        await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "⏭️ Pular conteúdo"},
            uid=10,
            state=state,
            payload=payload,
        )
        assert db.conn.execute("SELECT status FROM course_contents WHERE id=?", (second,)).fetchone()[0] == "skipped"
        # Resolver o último conteúdo não encerra o curso silenciosamente.
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()[0] == "active"

        progress = await course_domain.progress_summary(db, 10, course_id)
        assert progress == {
            "total": 2,
            "completed": 1,
            "skipped": 1,
            "pending": 0,
            "percent_completed": 50.0,
            "percent_resolved": 100.0,
        }
        assert any("só muda" in text.lower() for text, _ in sent)

    asyncio.run(scenario())


def test_course_completion_requires_confirmation_and_can_be_reopened(monkeypatch):
    async def scenario():
        db = FakeD1()

        async def fake_send(token, chat_id, text, reply_markup=None):
            return {"ok": True}

        monkeypatch.setattr(course_operational, "send_message", fake_send)
        course_stage4.install()
        course_id, _, _, _ = await _fixture_course(db)

        await course_stage4._show_course(db, "token", 1010, 10, course_id)
        state, payload = await _state(db)
        await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "🏁 Concluir curso"},
            uid=10,
            state=state,
            payload=payload,
        )
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()[0] == "active"
        state, payload = await _state(db)
        assert state == "course_complete_confirm"

        await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "🏁 Confirmar conclusão"},
            uid=10,
            state=state,
            payload=payload,
        )
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()[0] == "completed"

        state, payload = await _state(db)
        assert state == "course_view"
        await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "↩️ Reabrir curso"},
            uid=10,
            state=state,
            payload=payload,
        )
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()[0] == "active"

    asyncio.run(scenario())


def test_completed_or_skipped_content_can_return_to_pending(monkeypatch):
    async def scenario():
        db = FakeD1()

        async def fake_send(token, chat_id, text, reply_markup=None):
            return {"ok": True}

        monkeypatch.setattr(course_operational, "send_message", fake_send)
        course_stage4.install()
        course_id, module_id, first, _ = await _fixture_course(db)
        await course_domain.set_content_status(db, 10, course_id, first, "completed")
        await course_stage4._show_content(db, "token", 1010, 10, course_id, module_id, first)
        state, payload = await _state(db)

        await course_stage4.handle_message(
            db,
            "token",
            {"chat": {"id": 1010}, "text": "↩️ Voltar para pendente"},
            uid=10,
            state=state,
            payload=payload,
        )
        row = db.conn.execute(
            "SELECT status,completed_at,skipped_at FROM course_contents WHERE id=?", (first,)
        ).fetchone()
        assert tuple(row) == ("pending", None, None)

    asyncio.run(scenario())


def test_cross_user_cannot_operate_course_progress(monkeypatch):
    async def scenario():
        db = FakeD1()

        async def fake_send(token, chat_id, text, reply_markup=None):
            return {"ok": True}

        monkeypatch.setattr(course_operational, "send_message", fake_send)
        course_stage4.install()
        course_id, module_id, first, _ = await _fixture_course(db)
        await app_state(db, 20, "course_content_view", {
            "course_id": course_id,
            "module_id": module_id,
            "content_id": first,
        })
        try:
            await course_domain.set_content_status(db, 20, course_id, first, "completed")
        except LookupError:
            pass
        else:
            raise AssertionError("outro usuário não pode alterar progresso")
        assert db.conn.execute("SELECT status FROM course_contents WHERE id=?", (first,)).fetchone()[0] == "pending"

    asyncio.run(scenario())


async def app_state(db, uid, state, payload):
    await db.prepare(
        "INSERT INTO user_sessions(user_id,state,payload,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP) "
        "ON CONFLICT(user_id) DO UPDATE SET state=excluded.state,payload=excluded.payload,updated_at=CURRENT_TIMESTAMP"
    ).bind(uid, state, json.dumps(payload)).run()
