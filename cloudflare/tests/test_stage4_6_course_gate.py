import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import course_domain
import course_importer
import course_study_bridge
import study_mode


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
        self.conn.executemany(
            "INSERT INTO users(id,telegram_chat_id,is_owner) VALUES(?,?,?)",
            [(10, 1010, 1), (20, 2020, 0)],
        )
        self.conn.executescript(Path("migrations/0011_study_mode.sql").read_text(encoding="utf-8"))
        self.conn.executescript(Path("migrations/0013_courses.sql").read_text(encoding="utf-8"))
        self.conn.executescript(Path("migrations/0014_course_study_links.sql").read_text(encoding="utf-8"))
        self.conn.commit()

    def prepare(self, sql):
        return Statement(self.conn, sql)


def test_gate_self_paced_order_explicit_progress_and_history():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Backend")
        mod1 = await course_domain.add_module(db, 10, course_id, "Base", position=1)
        mod2 = await course_domain.add_module(db, 10, course_id, "Avançado", position=2)
        c1 = await course_domain.add_content(db, 10, course_id, mod1, "HTTP", position=1)
        c2 = await course_domain.add_content(db, 10, course_id, mod2, "Segurança", position=1)

        nxt = await course_domain.next_content(db, 10, course_id)
        assert nxt["id"] == c1
        await course_domain.set_content_status(db, 10, course_id, c1, "completed")
        nxt = await course_domain.next_content(db, 10, course_id)
        assert nxt["id"] == c2
        await course_domain.set_content_status(db, 10, course_id, c2, "skipped")

        assert await course_domain.next_content(db, 10, course_id) is None
        # Resolver todos os conteúdos não conclui o curso.
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()[0] == "active"
        await course_domain.set_course_status(db, 10, course_id, "completed")
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()[0] == "completed"

        events = [r[0] for r in db.conn.execute(
            "SELECT event_type FROM course_events WHERE course_id=? ORDER BY id", (course_id,)
        ).fetchall()]
        assert "content_completed" in events
        assert "content_skipped" in events
        assert events[-1] == "course_completed"

    asyncio.run(scenario())


def test_gate_live_course_uses_persisted_calendar_for_continue_order():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Ao vivo", mode="live")
        module_id = await course_domain.add_module(db, 10, course_id, "Semana")
        later = await course_domain.add_content(
            db, 10, course_id, module_id, "Aula 2", position=1, scheduled_at="2026-09-20T19:00"
        )
        earlier = await course_domain.add_content(
            db, 10, course_id, module_id, "Aula 1", position=2, scheduled_at="2026-09-15T19:00"
        )
        unscheduled = await course_domain.add_content(
            db, 10, course_id, module_id, "Material extra", position=3
        )

        assert (await course_domain.next_content(db, 10, course_id))["id"] == earlier
        await course_domain.set_content_status(db, 10, course_id, earlier, "completed")
        assert (await course_domain.next_content(db, 10, course_id))["id"] == later
        await course_domain.set_content_status(db, 10, course_id, later, "completed")
        assert (await course_domain.next_content(db, 10, course_id))["id"] == unscheduled

    asyncio.run(scenario())


def test_gate_import_study_and_course_progress_remain_separate():
    async def scenario():
        db = FakeD1()
        plan = course_importer.parse_course_text(
            "CURSO: APIs\nTIPO: AUTOGERIDO\n[MÓDULO] REST\n[CONTEÚDO] Controllers | aula"
        )
        course_id = await course_importer.persist_plan(db, 10, plan)
        content = db.conn.execute(
            "SELECT id,status FROM course_contents ORDER BY id LIMIT 1"
        ).fetchone()
        assert content["status"] == "pending"

        started = await course_study_bridge.start_content_study(db, 10, course_id, content["id"])
        session = await db.prepare("SELECT * FROM study_sessions WHERE id=?").bind(started["session_id"]).first()
        await study_mode._mark_topic(db, session, "completed")
        assert db.conn.execute(
            "SELECT status FROM course_contents WHERE id=?", (content["id"],)
        ).fetchone()[0] == "pending"

        await course_domain.set_content_status(db, 10, course_id, content["id"], "completed")
        assert db.conn.execute(
            "SELECT status FROM course_contents WHERE id=?", (content["id"],)
        ).fetchone()[0] == "completed"
        assert db.conn.execute("SELECT status FROM courses WHERE id=?", (course_id,)).fetchone()[0] == "active"

    asyncio.run(scenario())


def test_gate_multiuser_isolation_covers_structure_progress_and_study_links():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Privado")
        module_id = await course_domain.add_module(db, 10, course_id, "M1")
        content_id = await course_domain.add_content(db, 10, course_id, module_id, "Segredo")

        assert await course_domain.list_courses(db, 20) == []
        for operation in (
            lambda: course_domain.course_structure(db, 20, course_id),
            lambda: course_domain.set_content_status(db, 20, course_id, content_id, "completed"),
            lambda: course_study_bridge.start_content_study(db, 20, course_id, content_id),
        ):
            try:
                await operation()
            except LookupError:
                pass
            else:
                raise AssertionError("isolamento multiusuário falhou")

        assert db.conn.execute("SELECT status FROM course_contents WHERE id=?", (content_id,)).fetchone()[0] == "pending"
        assert db.conn.execute("SELECT COUNT(*) FROM course_study_links").fetchone()[0] == 0

    asyncio.run(scenario())


def test_gate_import_preview_is_non_mutating():
    db = FakeD1()
    plan = course_importer.parse_course_text(
        "CURSO: Preview\nTIPO: AUTOGERIDO\n[MÓDULO] M1\n[CONTEÚDO] C1 | leitura"
    )
    text = course_importer.preview_text(plan)
    assert "Nada foi salvo ainda" in text
    assert db.conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0
