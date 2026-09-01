import asyncio
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import course_domain
import course_operational
import operational_menu


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
        migration = Path("migrations/0013_courses.sql").read_text(encoding="utf-8")
        self.conn.executescript(migration)
        self.conn.commit()

    def prepare(self, sql):
        return Statement(self.conn, sql)


async def _state(db, uid=10):
    row = db.conn.execute("SELECT state,payload FROM user_sessions WHERE user_id=?", (uid,)).fetchone()
    if not row:
        return None, {}
    return row["state"], json.loads(row["payload"] or "{}")


def test_main_menu_exposes_structured_courses_without_reusing_later_backlog_button():
    flat = [button for row in operational_menu.MAIN_KB for button in row]
    assert "📘 Cursos" in flat
    assert "🎓 Cursos" not in flat
    assert operational_menu.MAIN_KB[-1] == ["🌙 Day-off"]


def test_domain_crud_helpers_preserve_progress_and_user_isolation():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Spring")
        module_id = await course_domain.add_module(db, 10, course_id, "Base")
        content_id = await course_domain.add_content(db, 10, course_id, module_id, "REST")

        await course_domain.update_course(
            db,
            10,
            course_id,
            title="Spring Boot",
            mode="live",
            description="Curso principal",
        )
        await course_domain.rename_module(db, 10, course_id, module_id, "Fundamentos")
        await course_domain.update_content(
            db,
            10,
            course_id,
            content_id,
            title="REST Controllers",
            kind="lesson",
            scheduled_at="2026-09-15T19:30",
        )

        course = await course_domain.get_course(db, 10, course_id)
        assert course["title"] == "Spring Boot"
        assert course["mode"] == "live"
        structure = await course_domain.course_structure(db, 10, course_id)
        assert structure["modules"][0]["title"] == "Fundamentos"
        assert structure["modules"][0]["contents"][0]["title"] == "REST Controllers"
        assert structure["modules"][0]["contents"][0]["status"] == "pending"

        mine = await course_domain.list_courses(db, 10)
        theirs = await course_domain.list_courses(db, 20)
        assert [row["id"] for row in mine] == [course_id]
        assert theirs == []

        for action in (
            lambda: course_domain.update_course(db, 20, course_id, title="Invasão"),
            lambda: course_domain.rename_module(db, 20, course_id, module_id, "Invasão"),
            lambda: course_domain.update_content(db, 20, course_id, content_id, title="Invasão"),
        ):
            try:
                await action()
            except LookupError:
                pass
            else:
                raise AssertionError("edição cruzada entre usuários deveria ser bloqueada")

    asyncio.run(scenario())


def test_telegram_wizard_creates_course_module_and_content_without_fake_progress(monkeypatch):
    async def scenario():
        db = FakeD1()
        sent = []

        async def fake_send(token, chat_id, text, reply_markup=None):
            sent.append((chat_id, text, reply_markup))
            return {"ok": True}

        monkeypatch.setattr(course_operational, "send_message", fake_send)

        async def say(text):
            return await course_operational.handle_message(
                db,
                "token",
                {"chat": {"id": 1010}, "text": text},
            )

        assert await say("📘 Cursos") is True
        assert await say("➕ Novo curso") is True
        assert (await _state(db))[0] == "course_create_title"
        await say("Java + Spring")
        assert (await _state(db))[0] == "course_create_mode"
        await say("🧭 Autogerido")
        assert (await _state(db))[0] == "course_create_description"
        await say("Trilha de backend")

        course = db.conn.execute("SELECT id,title,mode,status FROM courses WHERE user_id=10").fetchone()
        assert course["title"] == "Java + Spring"
        assert course["mode"] == "self_paced"
        assert course["status"] == "active"
        assert (await _state(db))[0] == "course_view"

        await say("➕ Novo módulo")
        await say("Fundamentos")
        assert (await _state(db))[0] == "course_module_view"

        await say("➕ Novo conteúdo")
        await say("REST Controllers")
        await say("🎥 Aula")
        state, payload = await _state(db)
        assert state == "course_content_view"
        content_id = payload["content_id"]

        row = db.conn.execute("SELECT title,kind,status FROM course_contents WHERE id=?", (content_id,)).fetchone()
        assert row["title"] == "REST Controllers"
        assert row["kind"] == "lesson"
        assert row["status"] == "pending"

        # Abrir, navegar e editar metadados não pode virar conclusão implícita.
        await say("✏️ Editar conteúdo")
        await say("✏️ Nome")
        await say("Controllers REST")
        row = db.conn.execute("SELECT title,status FROM course_contents WHERE id=?", (content_id,)).fetchone()
        assert row["title"] == "Controllers REST"
        assert row["status"] == "pending"
        assert any("progresso" in text.lower() for _, text, _ in sent if text)

    asyncio.run(scenario())


def test_live_course_wizard_normalizes_schedule_and_archive_is_reversible(monkeypatch):
    async def scenario():
        db = FakeD1()

        async def fake_send(token, chat_id, text, reply_markup=None):
            return {"ok": True}

        monkeypatch.setattr(course_operational, "send_message", fake_send)

        async def say(text):
            return await course_operational.handle_message(
                db,
                "token",
                {"chat": {"id": 1010}, "text": text},
            )

        await say("➕ Novo curso")
        await say("Curso ao vivo")
        await say("📡 Ao vivo")
        await say("⏭️ Sem descrição")
        state, payload = await _state(db)
        course_id = payload["course_id"]

        await say("➕ Novo módulo")
        await say("Semana 1")
        await say("➕ Novo conteúdo")
        await say("Aula síncrona")
        await say("🎥 Aula")
        assert (await _state(db))[0] == "course_add_content_schedule"
        await say("15/09/2026 19:30")

        row = db.conn.execute(
            "SELECT scheduled_at,status FROM course_contents ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row["scheduled_at"] == "2026-09-15T19:30"
        assert row["status"] == "pending"

        await say("⬅️ Voltar ao módulo")
        await say("⬅️ Voltar ao curso")
        await say("🗄️ Arquivar curso")
        assert (await _state(db))[0] == "course_archive_confirm"
        await say("✅ Arquivar curso")
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()["status"] == "archived"

        archived = await course_domain.list_courses(db, 10, statuses=("archived",))
        assert [row["id"] for row in archived] == [course_id]

        await say("🗄️ Cursos arquivados")
        await say(course_operational._course_button(archived[0], archived=True))
        await say("♻️ Reativar curso")
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()["status"] == "active"

    asyncio.run(scenario())


def test_cancelled_course_wizard_persists_nothing(monkeypatch):
    async def scenario():
        db = FakeD1()

        async def fake_send(token, chat_id, text, reply_markup=None):
            return {"ok": True}

        monkeypatch.setattr(course_operational, "send_message", fake_send)
        await course_operational.handle_message(
            db, "token", {"chat": {"id": 1010}, "text": "➕ Novo curso"}
        )
        await course_operational.handle_message(
            db, "token", {"chat": {"id": 1010}, "text": "Curso temporário"}
        )
        await course_operational.handle_message(
            db, "token", {"chat": {"id": 1010}, "text": "❌ Cancelar ação"}
        )

        assert db.conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0
        assert (await _state(db))[0] is None

    asyncio.run(scenario())
