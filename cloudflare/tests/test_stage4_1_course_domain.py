import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import course_domain


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
        self.conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_chat_id INTEGER UNIQUE)")
        self.conn.executemany(
            "INSERT INTO users(id,telegram_chat_id) VALUES(?,?)",
            [(10, 1010), (20, 2020)],
        )
        migration = Path("migrations/0013_courses.sql").read_text(encoding="utf-8")
        self.conn.executescript(migration)
        self.conn.commit()

    def prepare(self, sql):
        return Statement(self.conn, sql)


def test_self_paced_course_keeps_structural_order_without_auto_progress():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Spring Boot")
        m1 = await course_domain.add_module(db, 10, course_id, "Fundamentos")
        m2 = await course_domain.add_module(db, 10, course_id, "Persistência")
        c1 = await course_domain.add_content(db, 10, course_id, m1, "IoC e DI")
        c2 = await course_domain.add_content(db, 10, course_id, m1, "REST Controllers")
        await course_domain.add_content(db, 10, course_id, m2, "JPA")

        nxt = await course_domain.next_content(db, 10, course_id)
        assert nxt["id"] == c1
        assert nxt["title"] == "IoC e DI"

        # Apenas consultar/ordenar nunca altera progresso.
        assert db.conn.execute("SELECT status FROM course_contents WHERE id=?", (c1,)).fetchone()["status"] == "pending"
        assert db.conn.execute("SELECT status FROM course_contents WHERE id=?", (c2,)).fetchone()["status"] == "pending"

        structure = await course_domain.course_structure(db, 10, course_id)
        assert [m["title"] for m in structure["modules"]] == ["Fundamentos", "Persistência"]
        assert [c["title"] for c in structure["modules"][0]["contents"]] == ["IoC e DI", "REST Controllers"]

    asyncio.run(scenario())


def test_content_and_course_completion_are_both_explicit():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Java")
        module_id = await course_domain.add_module(db, 10, course_id, "POO")
        c1 = await course_domain.add_content(db, 10, course_id, module_id, "Classes")
        c2 = await course_domain.add_content(db, 10, course_id, module_id, "Herança")

        await course_domain.set_content_status(db, 10, course_id, c1, "completed")
        progress = await course_domain.progress_summary(db, 10, course_id)
        assert progress == {
            "total": 2,
            "completed": 1,
            "skipped": 0,
            "pending": 1,
            "percent_completed": 50.0,
            "percent_resolved": 50.0,
        }
        assert (await course_domain.next_content(db, 10, course_id))["id"] == c2

        await course_domain.set_content_status(db, 10, course_id, c2, "completed")
        assert await course_domain.next_content(db, 10, course_id) is None

        # Mesmo com tudo resolvido, o curso não se conclui sozinho.
        row = db.conn.execute("SELECT status,completed_at FROM courses WHERE id=?", (course_id,)).fetchone()
        assert row["status"] == "active"
        assert row["completed_at"] is None

        await course_domain.set_course_status(db, 10, course_id, "completed")
        row = db.conn.execute("SELECT status,completed_at FROM courses WHERE id=?", (course_id,)).fetchone()
        assert row["status"] == "completed"
        assert row["completed_at"] is not None

    asyncio.run(scenario())


def test_skipped_is_resolved_but_not_counted_as_completed():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Git")
        module_id = await course_domain.add_module(db, 10, course_id, "Base")
        c1 = await course_domain.add_content(db, 10, course_id, module_id, "Init")
        c2 = await course_domain.add_content(db, 10, course_id, module_id, "Rebase")
        await course_domain.set_content_status(db, 10, course_id, c1, "skipped")

        progress = await course_domain.progress_summary(db, 10, course_id)
        assert progress["completed"] == 0
        assert progress["skipped"] == 1
        assert progress["percent_completed"] == 0.0
        assert progress["percent_resolved"] == 50.0
        assert (await course_domain.next_content(db, 10, course_id))["id"] == c2

    asyncio.run(scenario())


def test_live_course_prefers_scheduled_order():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Curso ao vivo", mode="live")
        module_id = await course_domain.add_module(db, 10, course_id, "Semana 1")
        late = await course_domain.add_content(
            db, 10, course_id, module_id, "Aula de sexta", scheduled_at="2026-09-04T19:00:00"
        )
        early = await course_domain.add_content(
            db, 10, course_id, module_id, "Aula de terça", scheduled_at="2026-09-01T19:00:00"
        )
        unscheduled = await course_domain.add_content(db, 10, course_id, module_id, "Material extra")

        nxt = await course_domain.next_content(db, 10, course_id)
        assert nxt["id"] == early
        await course_domain.set_content_status(db, 10, course_id, early, "completed")
        assert (await course_domain.next_content(db, 10, course_id))["id"] == late
        await course_domain.set_content_status(db, 10, course_id, late, "completed")
        assert (await course_domain.next_content(db, 10, course_id))["id"] == unscheduled

    asyncio.run(scenario())


def test_materials_and_activities_belong_to_owned_content_and_progress_is_explicit():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Vue")
        module_id = await course_domain.add_module(db, 10, course_id, "Componentes")
        content_id = await course_domain.add_content(db, 10, course_id, module_id, "Props")
        material_id = await course_domain.add_material(
            db, 10, course_id, content_id, "Documentação", kind="link", reference="https://example.test/docs"
        )
        activity_id = await course_domain.add_activity(db, 10, course_id, content_id, "Criar componente")

        assert material_id is not None
        assert activity_id is not None
        row = db.conn.execute("SELECT status FROM course_activities WHERE id=?", (activity_id,)).fetchone()
        assert row["status"] == "pending"

        await course_domain.set_activity_status(db, 10, course_id, activity_id, "completed")
        row = db.conn.execute("SELECT status,completed_at FROM course_activities WHERE id=?", (activity_id,)).fetchone()
        assert row["status"] == "completed"
        assert row["completed_at"] is not None

        # Atividade concluída não conclui automaticamente o conteúdo-pai.
        row = db.conn.execute("SELECT status FROM course_contents WHERE id=?", (content_id,)).fetchone()
        assert row["status"] == "pending"

    asyncio.run(scenario())


def test_course_access_is_isolated_by_user():
    async def scenario():
        db = FakeD1()
        course_id = await course_domain.create_course(db, 10, "Privado")
        module_id = await course_domain.add_module(db, 10, course_id, "Módulo")
        content_id = await course_domain.add_content(db, 10, course_id, module_id, "Conteúdo")

        for action in (
            lambda: course_domain.course_structure(db, 20, course_id),
            lambda: course_domain.next_content(db, 20, course_id),
            lambda: course_domain.set_content_status(db, 20, course_id, content_id, "completed"),
            lambda: course_domain.add_module(db, 20, course_id, "Invasão"),
        ):
            try:
                await action()
            except LookupError:
                pass
            else:
                raise AssertionError("outro usuário acessou curso alheio")

    asyncio.run(scenario())


def test_schema_rejects_invalid_enums():
    db = FakeD1()
    for sql, params in (
        ("INSERT INTO courses(user_id,title,mode) VALUES(?,?,?)", (10, "X", "random")),
        ("INSERT INTO courses(user_id,title,status) VALUES(?,?,?)", (10, "Y", "finished-ish")),
    ):
        try:
            db.conn.execute(sql, params)
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("CHECK constraint deveria rejeitar enum inválido")
