import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import course_domain
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


async def _course(db):
    course_id = await course_domain.create_course(db, 10, "Spring Boot")
    module_id = await course_domain.add_module(db, 10, course_id, "API")
    first = await course_domain.add_content(db, 10, course_id, module_id, "Controllers")
    second = await course_domain.add_content(db, 10, course_id, module_id, "JPA")
    return course_id, first, second


def test_study_session_keeps_course_progress_independent():
    async def scenario():
        db = FakeD1()
        course_id, content_id, _ = await _course(db)

        started = await course_study_bridge.start_content_study(db, 10, course_id, content_id)
        assert started["content_title"] == "Controllers"
        assert started["focus_minutes"] == study_mode.DEFAULT_FOCUS_MINUTES

        link = db.conn.execute(
            "SELECT user_id,course_id,content_id,study_session_id FROM course_study_links"
        ).fetchone()
        assert tuple(link) == (10, course_id, content_id, started["session_id"])
        assert db.conn.execute(
            "SELECT status FROM course_contents WHERE id=?", (content_id,)
        ).fetchone()[0] == "pending"

        session = await db.prepare("SELECT * FROM study_sessions WHERE id=?").bind(started["session_id"]).first()
        message = await study_mode._mark_topic(db, session, "completed")
        assert "Controllers" in message

        # Nem concluir o tópico nem a sessão de estudo conclui o conteúdo do curso.
        assert db.conn.execute(
            "SELECT status FROM study_sessions WHERE id=?", (started["session_id"],)
        ).fetchone()[0] == "completed"
        assert db.conn.execute(
            "SELECT status FROM course_contents WHERE id=?", (content_id,)
        ).fetchone()[0] == "pending"
        assert db.conn.execute(
            "SELECT status FROM courses WHERE id=?", (course_id,)
        ).fetchone()[0] == "active"

        events = [
            row[0]
            for row in db.conn.execute(
                "SELECT event_type FROM course_events WHERE course_id=? ORDER BY id", (course_id,)
            ).fetchall()
        ]
        assert "course_study_started" in events

    asyncio.run(scenario())


def test_existing_study_session_blocks_silent_replacement():
    async def scenario():
        db = FakeD1()
        course_id, first, second = await _course(db)
        await course_study_bridge.start_content_study(db, 10, course_id, first)

        try:
            await course_study_bridge.start_content_study(db, 10, course_id, second)
        except course_study_bridge.StudySessionBusy:
            pass
        else:
            raise AssertionError("sessão ativa não pode ser substituída silenciosamente")

        assert db.conn.execute("SELECT COUNT(*) FROM study_sessions WHERE user_id=10").fetchone()[0] == 1
        assert db.conn.execute("SELECT COUNT(*) FROM course_study_links WHERE user_id=10").fetchone()[0] == 1

    asyncio.run(scenario())


def test_study_bridge_respects_course_ownership():
    async def scenario():
        db = FakeD1()
        course_id, content_id, _ = await _course(db)
        try:
            await course_study_bridge.start_content_study(db, 20, course_id, content_id)
        except LookupError:
            pass
        else:
            raise AssertionError("outro usuário não pode iniciar estudo a partir desse curso")

        assert db.conn.execute("SELECT COUNT(*) FROM course_study_links").fetchone()[0] == 0
        assert db.conn.execute("SELECT COUNT(*) FROM study_sessions WHERE user_id=20").fetchone()[0] == 0

    asyncio.run(scenario())


def test_non_pending_content_cannot_start_course_study():
    async def scenario():
        db = FakeD1()
        course_id, content_id, _ = await _course(db)
        await course_domain.set_content_status(db, 10, course_id, content_id, "completed")
        try:
            await course_study_bridge.start_content_study(db, 10, course_id, content_id)
        except ValueError:
            pass
        else:
            raise AssertionError("conteúdo resolvido não deve iniciar nova sessão pela ação de pendente")

        assert db.conn.execute("SELECT COUNT(*) FROM study_sessions").fetchone()[0] == 0

    asyncio.run(scenario())
