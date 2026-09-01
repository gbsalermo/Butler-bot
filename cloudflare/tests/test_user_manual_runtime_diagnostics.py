import asyncio
import inspect
import sqlite3

import runtime_diagnostics
import start_reset
import user_manual
import worker


class Result:
    def __init__(self, results=None):
        self.results = results or []


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
        return cur.fetchone()

    async def all(self):
        cur = self.conn.execute(self.sql, self.params)
        return Result(list(cur.fetchall()))

    async def run(self):
        cur = self.conn.execute(self.sql, self.params)
        self.conn.commit()
        return Result()


class FakeD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def prepare(self, sql):
        return Statement(self.conn, sql)


def test_manual_documents_new_time_and_study_features():
    overview = user_manual._overview()
    tempo = user_manual._section_text("tempo")
    estudo = user_manual._section_text("estudo")

    assert "cronometra 20 minutos" in overview
    assert "modo estudo" in overview.lower()
    assert "cancelar timer #12" in tempo
    assert "não viram tarefa" in tempo
    assert "concluí o tópico" in estudo
    assert "nunca conclui tópico sozinho" in estudo


def test_manual_section_aliases_are_easy_to_recall():
    assert user_manual._section_from_text("Ajuda: Tempo") == "tempo"
    assert user_manual._section_from_text("ajuda estudo") == "estudo"
    assert user_manual._section_from_text("Ajuda: Faculdade") == "faculdade"
    assert user_manual._section_from_text("Ajuda: Musculação") == "treino"


def test_manual_and_runtime_status_are_checked_before_start_reset_logic():
    source = inspect.getsource(start_reset.handle_start_reset)
    manual = source.index("handle_user_manual")
    runtime = source.index("handle_runtime_diagnostics")
    start_check = source.index('text not in ("/start"')
    assert runtime < manual < start_check


def test_runtime_error_is_persisted_without_conversation_text():
    async def scenario():
        db = FakeD1()
        runtime_diagnostics._SCHEMA_READY = False
        await runtime_diagnostics.record_error(
            db,
            "fetch:/telegram/webhook",
            RuntimeError("falha de teste"),
            chat_id=123,
        )
        row = db.conn.execute(
            "SELECT scope,error_type,error_message,chat_id FROM runtime_errors"
        ).fetchone()
        assert row["scope"] == "fetch:/telegram/webhook"
        assert row["error_type"] == "RuntimeError"
        assert row["error_message"] == "falha de teste"
        assert row["chat_id"] == 123
        columns = {
            r[1]
            for r in db.conn.execute("PRAGMA table_info(runtime_errors)").fetchall()
        }
        assert "message_text" not in columns
        assert "conversation" not in columns

    asyncio.run(scenario())


def test_runtime_status_detects_stage3_tables_and_latest_error():
    async def scenario():
        db = FakeD1()
        runtime_diagnostics._SCHEMA_READY = False
        await runtime_diagnostics.ensure_schema(db)
        db.conn.execute("CREATE TABLE quick_timers (id INTEGER PRIMARY KEY)")
        db.conn.execute("CREATE TABLE study_sessions (id INTEGER PRIMARY KEY)")
        db.conn.commit()
        await runtime_diagnostics.record_error(db, "scheduled", ValueError("boom"))

        text = await runtime_diagnostics.runtime_status_text(db)
        assert "D1: ✅ acessível" in text
        assert "quick_timers: ✅" in text
        assert "study_sessions: ✅" in text
        assert "ValueError: boom" in text

    asyncio.run(scenario())


def test_worker_records_unhandled_fetch_errors_instead_of_silent_failure():
    source = inspect.getsource(worker.Default.fetch)
    assert "record_error" in source
    assert "fetch:{path}" in source
    assert "handler error recorded" in source
