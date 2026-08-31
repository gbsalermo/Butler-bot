import asyncio
import inspect
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import core_fast_path
import personal_alarm
import study_mode


class Result:
    def __init__(self, results=None, last_row_id=None):
        self.results = results or []
        self.meta = {"last_row_id": last_row_id}


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
        self.conn.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                telegram_chat_id INTEGER NOT NULL UNIQUE
            );
            CREATE TABLE subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                notification_key TEXT NOT NULL,
                UNIQUE(user_id, notification_key)
            );
            """
        )
        self.conn.executemany(
            "INSERT INTO users(id,telegram_chat_id) VALUES(?,?)",
            [(10, 1010), (20, 2020)],
        )
        self.conn.executemany(
            "INSERT INTO subjects(user_id,name,active) VALUES(?,?,1)",
            [(10, "Cálculo I"), (20, "Física I")],
        )
        self.conn.commit()

    def prepare(self, sql):
        return Statement(self.conn, sql)


def _config(focus=25, pause=5, long_pause=15):
    return {
        "focus_minutes": focus,
        "break_minutes": pause,
        "long_break_minutes": long_pause,
        "long_break_every": 4,
    }


def _fresh_db():
    db = FakeD1()
    study_mode._SCHEMA_READY = False
    return db


def test_candidate_guard_does_not_hijack_future_planning():
    assert study_mode.is_study_candidate("quero estudar cálculo amanhã") is False
    assert study_mode.is_study_candidate("quero estudar cálculo agora: limites, derivadas") is True
    assert study_mode.is_study_candidate("modo estudo Cálculo: limites") is True
    assert study_mode.is_study_candidate("status estudo") is True


def test_start_parser_supports_defaults_custom_cycle_and_topics():
    parsed = study_mode._parse_start("modo estudo Cálculo: limites, derivadas e integrais")
    assert parsed["focus_minutes"] == 25
    assert parsed["break_minutes"] == 5
    assert parsed["long_break_minutes"] == 15
    assert parsed["subject"] == "Cálculo"
    assert parsed["topics"] == ["limites", "derivadas", "integrais"]

    custom = study_mode._parse_start("modo estudo 50/10/20 Física: cinemática, dinâmica")
    assert custom["focus_minutes"] == 50
    assert custom["break_minutes"] == 10
    assert custom["long_break_minutes"] == 20
    assert custom["topics"] == ["cinemática", "dinâmica"]


def test_unaccented_comeca_is_parsed_as_start_command():
    parsed = study_mode._parse_start("comeca o modo estudo Cálculo: limites, derivadas")
    assert parsed["subject"] == "Cálculo"
    assert parsed["topics"] == ["limites", "derivadas"]


def test_invalid_cycle_ranges_are_rejected():
    assert study_mode._parse_start("modo estudo 2/5 Cálculo: limites")["error"]
    assert study_mode._parse_start("modo estudo 25/0 Cálculo: limites")["error"]
    assert study_mode._parse_start("modo estudo 25/5/2 Cálculo: limites")["error"]


def test_create_session_persists_topics_and_canonical_subject():
    async def scenario():
        db = _fresh_db()
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        session, topic = await study_mode._create_session(
            db, 10, "calculo i", ["Limites", "Derivadas"], _config(), now=base
        )
        assert session["subject_name"] == "Cálculo I"
        assert session["phase"] == "focus"
        assert study_mode._parse_iso(session["phase_ends_at"]) == base + timedelta(minutes=25)
        assert topic["title"] == "Limites"
        topics = db.conn.execute(
            "SELECT position,title,status FROM study_topics WHERE session_id=? ORDER BY position",
            (session["id"],),
        ).fetchall()
        assert [(r["position"], r["title"], r["status"]) for r in topics] == [
            (1, "Limites", "pending"),
            (2, "Derivadas", "pending"),
        ]

    asyncio.run(scenario())


def test_focus_expiry_starts_break_but_never_completes_topic(monkeypatch):
    async def scenario():
        db = _fresh_db()
        sent = []

        async def fake_send(token, chat, text, **kwargs):
            sent.append((chat, text))

        monkeypatch.setattr(study_mode.quality_patch, "send_message", fake_send)
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        session, topic = await study_mode._create_session(
            db, 10, "Cálculo I", ["Limites", "Derivadas"], _config(), now=base
        )
        await study_mode.dispatch_due_study(db, "token", now=base + timedelta(minutes=26))

        updated = db.conn.execute(
            "SELECT phase,cycles_completed FROM study_sessions WHERE id=?", (session["id"],)
        ).fetchone()
        topic_row = db.conn.execute(
            "SELECT status FROM study_topics WHERE id=?", (topic["id"],)
        ).fetchone()
        assert updated["phase"] == "break"
        assert updated["cycles_completed"] == 1
        assert topic_row["status"] == "pending"
        assert "o tópico não" in sent[0][1].lower()

    asyncio.run(scenario())


def test_break_expiry_returns_to_same_pending_topic(monkeypatch):
    async def scenario():
        db = _fresh_db()

        async def fake_send(*args, **kwargs):
            return None

        monkeypatch.setattr(study_mode.quality_patch, "send_message", fake_send)
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        session, topic = await study_mode._create_session(
            db, 10, "Cálculo I", ["Limites", "Derivadas"], _config(), now=base
        )
        await study_mode.dispatch_due_study(db, "token", now=base + timedelta(minutes=26))
        after_focus = db.conn.execute(
            "SELECT * FROM study_sessions WHERE id=?", (session["id"],)
        ).fetchone()
        break_end = study_mode._parse_iso(after_focus["phase_ends_at"])
        await study_mode.dispatch_due_study(db, "token", now=break_end + timedelta(seconds=1))

        after_break = db.conn.execute(
            "SELECT phase FROM study_sessions WHERE id=?", (session["id"],)
        ).fetchone()
        current = await study_mode._current_topic(db, session["id"])
        assert after_break["phase"] == "focus"
        assert current["id"] == topic["id"]
        assert current["status"] == "pending"

    asyncio.run(scenario())


def test_explicit_completion_moves_progress_and_keeps_real_focus_topic_in_history():
    async def scenario():
        db = _fresh_db()
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        session, first = await study_mode._create_session(
            db, 10, "Cálculo I", ["Limites", "Derivadas"], _config(), now=base
        )
        message = await study_mode._mark_topic(db, session, "completed", now=base + timedelta(minutes=10))
        assert "Limites" in message
        assert "Derivadas" in message

        first_row = db.conn.execute(
            "SELECT status FROM study_topics WHERE id=?", (first["id"],)
        ).fetchone()
        current = await study_mode._current_topic(db, session["id"])
        assert first_row["status"] == "completed"
        assert current["title"] == "Derivadas"

        focus_finished = db.conn.execute(
            "SELECT topic_id FROM study_events WHERE session_id=? AND event_type='focus_finished' ORDER BY id DESC LIMIT 1",
            (session["id"],),
        ).fetchone()
        assert focus_finished["topic_id"] == first["id"]

    asyncio.run(scenario())


def test_skip_and_final_completion_are_explicit():
    async def scenario():
        db = _fresh_db()
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        session, _ = await study_mode._create_session(
            db, 10, "Cálculo I", ["Limites", "Derivadas"], _config(), now=base
        )
        await study_mode._mark_topic(db, session, "skipped", now=base + timedelta(minutes=3))
        refreshed = db.conn.execute("SELECT * FROM study_sessions WHERE id=?", (session["id"],)).fetchone()
        await study_mode._mark_topic(db, refreshed, "completed", now=base + timedelta(minutes=4))

        statuses = [
            r["status"]
            for r in db.conn.execute(
                "SELECT status FROM study_topics WHERE session_id=? ORDER BY position", (session["id"],)
            ).fetchall()
        ]
        final = db.conn.execute(
            "SELECT status,phase FROM study_sessions WHERE id=?", (session["id"],)
        ).fetchone()
        assert statuses == ["skipped", "completed"]
        assert final["status"] == "completed"
        assert final["phase"] == "completed"

    asyncio.run(scenario())


def test_pause_resume_and_cancel_never_change_topic_status():
    async def scenario():
        db = _fresh_db()
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        session, topic = await study_mode._create_session(
            db, 10, "Cálculo I", ["Limites"], _config(), now=base
        )
        await study_mode._pause_session(db, session, now=base + timedelta(minutes=2))
        paused = db.conn.execute("SELECT * FROM study_sessions WHERE id=?", (session["id"],)).fetchone()
        assert paused["status"] == "paused"
        assert db.conn.execute("SELECT status FROM study_topics WHERE id=?", (topic["id"],)).fetchone()["status"] == "pending"

        await study_mode._resume_session(db, paused, now=base + timedelta(minutes=3))
        resumed = db.conn.execute("SELECT * FROM study_sessions WHERE id=?", (session["id"],)).fetchone()
        assert resumed["status"] == "active"
        assert resumed["phase"] == "focus"

        await study_mode._cancel_session(db, resumed, now=base + timedelta(minutes=4))
        cancelled = db.conn.execute("SELECT status,phase FROM study_sessions WHERE id=?", (session["id"],)).fetchone()
        assert cancelled["status"] == "cancelled"
        assert db.conn.execute("SELECT status FROM study_topics WHERE id=?", (topic["id"],)).fetchone()["status"] == "pending"

    asyncio.run(scenario())


def test_two_users_keep_independent_study_sessions():
    async def scenario():
        db = _fresh_db()
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        session_a, _ = await study_mode._create_session(db, 10, "Cálculo I", ["Limites"], _config(), now=base)
        session_b, _ = await study_mode._create_session(db, 20, "Física I", ["Dinâmica"], _config(), now=base)
        active_a = await study_mode._active_session(db, 10)
        active_b = await study_mode._active_session(db, 20)
        assert active_a["id"] == session_a["id"]
        assert active_b["id"] == session_b["id"]
        assert active_a["user_id"] != active_b["user_id"]

    asyncio.run(scenario())


def test_next_study_event_returns_phase_deadline():
    async def scenario():
        db = _fresh_db()
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        await study_mode._create_session(db, 10, "Cálculo I", ["Limites"], _config(40, 10, 20), now=base)
        assert await study_mode.next_study_event(db, 10, now=base) == base + timedelta(minutes=40)
        assert await study_mode.next_study_event(db, 20, now=base) is None

    asyncio.run(scenario())


def test_due_dispatch_is_idempotent(monkeypatch):
    async def scenario():
        db = _fresh_db()
        sent = []

        async def fake_send(token, chat, text, **kwargs):
            sent.append((chat, text))

        monkeypatch.setattr(study_mode.quality_patch, "send_message", fake_send)
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        session, _ = await study_mode._create_session(db, 10, "Cálculo I", ["Limites"], _config(), now=base)
        due = base + timedelta(minutes=26)
        await study_mode.dispatch_due_study(db, "token", now=due)
        await study_mode.dispatch_due_study(db, "token", now=due)
        assert len(sent) == 1
        logs = db.conn.execute(
            "SELECT COUNT(*) n FROM notification_log WHERE user_id=10 AND notification_key LIKE 'study:%'"
        ).fetchone()
        assert logs["n"] == 1
        current = db.conn.execute("SELECT phase FROM study_sessions WHERE id=?", (session["id"],)).fetchone()
        assert current["phase"] == "break"

    asyncio.run(scenario())


def test_history_uses_persisted_topic_progress():
    async def scenario():
        db = _fresh_db()
        base = datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc)
        session, _ = await study_mode._create_session(db, 10, "Cálculo I", ["Limites", "Derivadas"], _config(), now=base)
        await study_mode._mark_topic(db, session, "completed", now=base + timedelta(minutes=5))
        text = await study_mode._history_text(db, 10)
        assert "Cálculo I" in text
        assert "1/2 concluído" in text

    asyncio.run(scenario())


def test_core_places_study_before_compound_router():
    source = inspect.getsource(core_fast_path.handle_message)
    assert source.index("handle_study_mode") < source.index("handle_compound_message")


def test_personal_alarm_includes_study_candidate_and_dispatch():
    next_source = inspect.getsource(personal_alarm._next_event)
    alarm_source = inspect.getsource(personal_alarm.PersonalAlarm.alarm)
    assert "next_study_event" in next_source
    assert "dispatch_due_study" in alarm_source


def test_migration_0011_is_formal_source():
    path = Path(__file__).parents[1] / "migrations" / "0011_study_mode.sql"
    text = path.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS study_sessions" in text
    assert "CREATE TABLE IF NOT EXISTS study_topics" in text
    assert "CREATE TABLE IF NOT EXISTS study_events" in text
