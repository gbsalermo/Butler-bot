import asyncio
import sqlite3
from datetime import date

import short_context


class Statement:
    def __init__(self, conn, sql):
        self.conn = conn
        self.sql = sql
        self.params = ()

    def bind(self, *params):
        self.params = params
        return self

    async def first(self):
        cur = self.conn.execute(self.sql, self.params)
        row = cur.fetchone()
        return row

    async def run(self):
        self.conn.execute(self.sql, self.params)
        self.conn.commit()
        return None


class FakeD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE natural_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                target_id INTEGER,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE daily_items (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                due_date TEXT,
                due_time TEXT,
                status TEXT DEFAULT 'pendente'
            );
            """
        )

    def prepare(self, sql):
        return Statement(self.conn, sql)


def _seed(db):
    db.conn.executemany(
        "INSERT INTO daily_items(id,user_id,kind,title,due_date) VALUES(?,?,?,?,?)",
        [
            (1, 10, "tarefa", "Relatório", "2026-08-31"),
            (2, 10, "tarefa", "Mercado", "2026-08-31"),
            (3, 20, "tarefa", "README", "2026-08-31"),
            (4, 20, "tarefa", "Documentação", "2026-08-31"),
        ],
    )
    db.conn.commit()


def test_two_users_keep_independent_positional_context():
    async def scenario():
        db = FakeD1()
        _seed(db)
        await short_context.remember_list(db, 10, "tarefa", [1, 2], source="task_list")
        await short_context.remember_list(db, 20, "tarefa", [3, 4], source="task_list")

        user_a = await short_context.resolve_daily_item(db, 10, "conclui a segunda", kind="tarefa")
        user_b = await short_context.resolve_daily_item(db, 20, "conclui a segunda", kind="tarefa")

        assert user_a["id"] == 2
        assert user_a["user_id"] == 10
        assert user_b["id"] == 4
        assert user_b["user_id"] == 20

    asyncio.run(scenario())


def test_stale_context_is_not_resolved_from_db():
    async def scenario():
        db = FakeD1()
        _seed(db)
        await short_context.remember_list(db, 10, "tarefa", [1, 2], source="task_list")
        db.conn.execute("UPDATE natural_events SET created_at='2020-01-01 00:00:00' WHERE user_id=10")
        db.conn.commit()

        assert await short_context.latest(db, 10) is None
        assert await short_context.resolve_daily_item(db, 10, "conclui a segunda", kind="tarefa") is None

    asyncio.run(scenario())


def test_temporal_qualifier_is_reference_filter_not_reschedule_destination():
    base = date(2026, 8, 30)
    assert short_context.reference_due_date_qualifier(
        "cancela aquela de amanhã", today=base
    ) == date(2026, 8, 31)

    # Sexta aqui é o destino novo, portanto não pode ser usado para rejeitar o
    # item atual antes de o domínio executar a alteração.
    assert short_context.reference_due_date_qualifier(
        "muda ela pra sexta", today=base
    ) is None
