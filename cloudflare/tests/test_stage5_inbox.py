import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import core_actions
import inbox_domain
import inbox_operational
import operational_menu
import production_usability_patch


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
        self.conn.executescript(Path("migrations/0001_initial.sql").read_text(encoding="utf-8"))
        self.conn.executescript(Path("migrations/0002_app_state.sql").read_text(encoding="utf-8"))
        self.conn.executescript(Path("migrations/0015_inbox.sql").read_text(encoding="utf-8"))
        self.conn.executemany(
            "INSERT INTO users(id,telegram_chat_id,is_owner) VALUES(?,?,?)",
            [(10, 1010, 1), (20, 2020, 0)],
        )
        self.conn.executemany(
            "INSERT INTO user_sessions(user_id,state,payload) VALUES(?,NULL,'{}')",
            [(10,), (20,)],
        )
        self.conn.commit()

    def prepare(self, sql):
        return Statement(self.conn, sql)


def test_inbox_domain_capture_archive_reopen_and_isolation():
    async def scenario():
        db = FakeD1()
        item_id = await inbox_domain.capture(db, 10, "revisar autenticação do SGL")
        assert [r["id"] for r in await inbox_domain.list_items(db, 10)] == [item_id]
        assert await inbox_domain.list_items(db, 20) == []
        assert await inbox_domain.get_item(db, 20, item_id) is None

        await inbox_domain.archive(db, 10, item_id)
        assert await inbox_domain.list_items(db, 10) == []
        assert [r["id"] for r in await inbox_domain.list_items(db, 10, status="archived")] == [item_id]
        await inbox_domain.reopen(db, 10, item_id)
        assert [r["id"] for r in await inbox_domain.list_items(db, 10)] == [item_id]

    asyncio.run(scenario())


def test_natural_capture_requires_explicit_inbox_semantics():
    assert inbox_operational._natural_capture("joga na inbox: revisar autenticação do SGL") == (
        True,
        "revisar autenticação do SGL",
    )
    assert inbox_operational._natural_capture("anota estudar cálculo pra eu organizar depois") == (
        True,
        "estudar cálculo",
    )
    assert inbox_operational._natural_capture("anota isso pra eu organizar depois") == (True, "")
    assert inbox_operational._natural_capture("anota uma tarefa") == (False, None)
    assert inbox_operational._natural_capture("me lembra de estudar amanhã") == (False, None)


def test_dynamic_archived_button_survives_telegram_unicode_variant():
    assert inbox_operational._item_id("🗄️ #7 item antigo") == 7
    assert inbox_operational._item_id("📥 #8 item pendente") == 8


def test_conversion_to_daily_item_is_idempotent_and_marks_inbox_once():
    async def scenario():
        db = FakeD1()
        item_id = await inbox_domain.capture(db, 10, "entregar relatório")
        first = await core_actions.create_daily_item_from_inbox(
            db, 10, item_id, "tarefa", "entregar relatório", "2026-09-10", "18:00"
        )
        second = await core_actions.create_daily_item_from_inbox(
            db, 10, item_id, "tarefa", "entregar relatório", "2026-09-10", "18:00"
        )
        assert first == second
        assert db.conn.execute(
            "SELECT COUNT(*) FROM daily_items WHERE source_inbox_id=?", (item_id,)
        ).fetchone()[0] == 1
        await inbox_domain.mark_converted(db, 10, item_id, "tarefa", first)
        await inbox_domain.mark_converted(db, 10, item_id, "tarefa", first)
        item = await inbox_domain.get_item(db, 10, item_id)
        assert item["status"] == "converted"
        assert item["converted_target_id"] == first
        assert await inbox_domain.list_items(db, 10) == []

    asyncio.run(scenario())


def test_task_and_appointment_are_distinct_safe_conversion_targets():
    async def scenario():
        db = FakeD1()
        task_inbox = await inbox_domain.capture(db, 10, "comprar passagem")
        appointment_inbox = await inbox_domain.capture(db, 10, "reunião do projeto")
        task_id = await core_actions.create_daily_item_from_inbox(
            db, 10, task_inbox, "tarefa", "comprar passagem"
        )
        appointment_id = await core_actions.create_daily_item_from_inbox(
            db, 10, appointment_inbox, "compromisso", "reunião do projeto", "2026-09-12", "14:00"
        )
        assert task_id and appointment_id and task_id != appointment_id
        kinds = [r[0] for r in db.conn.execute("SELECT kind FROM daily_items ORDER BY id").fetchall()]
        assert kinds == ["tarefa", "compromisso"]

    asyncio.run(scenario())


def test_operational_natural_capture_then_process_to_task_without_duplication():
    async def scenario():
        db = FakeD1()
        sent = []

        async def fake_send(token, chat_id, text, reply_markup=None):
            sent.append((chat_id, text, reply_markup))
            return True

        original = inbox_operational.send_message
        inbox_operational.send_message = fake_send
        try:
            msg = {"chat": {"id": 1010}, "text": "joga na inbox: revisar autenticação do SGL"}
            assert await inbox_operational.handle_message(db, "token", msg)
            item = db.conn.execute("SELECT id,content,status FROM inbox_items").fetchone()
            assert item["content"] == "revisar autenticação do SGL"
            assert item["status"] == "pending"

            assert await inbox_operational.handle_message(
                db, "token", {"chat": {"id": 1010}, "text": f"📥 #{item['id']} revisar autenticação"}
            )
            assert await inbox_operational.handle_message(
                db, "token", {"chat": {"id": 1010}, "text": "🧭 Processar"}
            )
            assert await inbox_operational.handle_message(
                db, "token", {"chat": {"id": 1010}, "text": "✅ Virar tarefa"}
            )
            assert await inbox_operational.handle_message(
                db, "token", {"chat": {"id": 1010}, "text": "📌 Sem data"}
            )

            converted = db.conn.execute("SELECT * FROM inbox_items WHERE id=?", (item["id"],)).fetchone()
            assert converted["status"] == "converted"
            assert converted["converted_domain"] == "tarefa"
            assert db.conn.execute("SELECT COUNT(*) FROM daily_items").fetchone()[0] == 1
            assert any("não ficou uma cópia" in text for _, text, _ in sent)
        finally:
            inbox_operational.send_message = original

    asyncio.run(scenario())


def test_back_to_my_life_is_a_real_escape_route_from_inbox_state():
    async def scenario():
        db = FakeD1()
        sent = []

        async def fake_send(token, chat_id, text, reply_markup=None):
            sent.append((text, reply_markup))
            return True

        original = inbox_operational.send_message
        inbox_operational.send_message = fake_send
        try:
            item_id = await inbox_domain.capture(db, 10, "coisa para depois")
            await inbox_operational._show_item(db, "token", 1010, 10, item_id)
            state = db.conn.execute("SELECT state FROM user_sessions WHERE user_id=10").fetchone()[0]
            assert state == "inbox_view"
            assert await inbox_operational.handle_message(
                db, "token", {"chat": {"id": 1010}, "text": "⬅️ Minha vida"}
            )
            state = db.conn.execute("SELECT state FROM user_sessions WHERE user_id=10").fetchone()[0]
            assert state is None
            assert sent[-1][0] == "📋 Minha vida"
            assert sent[-1][1]["keyboard"] == operational_menu.MY_LIFE_KB
        finally:
            inbox_operational.send_message = original

    asyncio.run(scenario())


def test_inbox_enters_existing_minimal_menu_without_growing_root():
    before_root = [list(row) for row in operational_menu.MAIN_KB]
    production_usability_patch.install()
    assert operational_menu.MAIN_KB == before_root
    assert any("📥 Inbox" in row for row in operational_menu.MY_LIFE_KB)
    assert any("📥 Capturar na Inbox" in row for row in operational_menu.ADD_KB)
