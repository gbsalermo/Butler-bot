"""Regressão do fluxo de musculação com SQLite real e cliente Telegram simulado."""
import asyncio
import sqlite3
from datetime import datetime

import app
import workout_experience as ux
import workout_quick_log as quick


class Statement:
    def __init__(self, conn, sql):
        self.conn, self.sql, self.args = conn, sql, ()

    def bind(self, *args):
        self.args = args
        return self

    async def first(self):
        row = self.conn.execute(self.sql, self.args).fetchone()
        return dict(row) if row else None

    async def all(self):
        rows = self.conn.execute(self.sql, self.args).fetchall()
        return type("Rows", (), {"results": [dict(row) for row in rows]})()

    async def run(self):
        self.conn.execute(self.sql, self.args)
        self.conn.commit()


class DB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE users(id INTEGER PRIMARY KEY, telegram_chat_id INTEGER, is_owner INTEGER);
            INSERT INTO users VALUES(1, 10, 1);
            CREATE TABLE protocol_mass_state(
                user_id INTEGER PRIMARY KEY, current_week INTEGER NOT NULL DEFAULT 1,
                active INTEGER NOT NULL DEFAULT 0, started_at TEXT, finished_at TEXT
            );
            INSERT INTO protocol_mass_state(user_id,current_week,active) VALUES(1,1,0);
            CREATE TABLE user_sessions(user_id INTEGER PRIMARY KEY, state TEXT, payload TEXT, updated_at TEXT);
            INSERT INTO user_sessions VALUES(1, NULL, '{}', NULL);
            CREATE TABLE protocol_mass_set_logs(
                id INTEGER PRIMARY KEY, user_id INTEGER, week INTEGER, weekday TEXT,
                exercise_name TEXT, set_number INTEGER, load TEXT, reps TEXT, source_message_id INTEGER,
                UNIQUE(user_id,week,weekday,exercise_name,set_number),
                UNIQUE(user_id,source_message_id)
            );
            CREATE TABLE workout_set_logs(
                id INTEGER PRIMARY KEY, user_id INTEGER, workout_date TEXT, exercise_name TEXT,
                set_number INTEGER, load TEXT, reps TEXT, source_message_id INTEGER,
                UNIQUE(user_id,workout_date,exercise_name,set_number),
                UNIQUE(user_id,source_message_id)
            );
            CREATE TABLE workout_logs(user_id INTEGER, workout_date TEXT);
            CREATE TABLE protocol_mass_sessions(user_id INTEGER, training_date TEXT);
        """)

    def prepare(self, sql):
        return Statement(self.conn, sql)

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _setup(monkeypatch):
    db, sent = DB(), []
    today = app.now_local().date()
    day = app.WEEKDAY_NAMES[today.weekday()]
    weeks = {
        "1": {day: [{"name": "Supino reto", "series": 3, "reps": "10"}]},
        "2": {day: [{"name": "Supino inclinado", "series": 3, "reps": "12"}]},
        "3": {},
    }
    monkeypatch.setattr(app, "WEEKS", weeks)
    monkeypatch.setattr(ux, "is_owner", lambda _: True)
    monkeypatch.setattr(quick, "is_owner", lambda _: True)
    async def send(_token, _chat, text, reply_markup=None, **_kw):
        sent.append((text, reply_markup))
        return {"ok": True}
    monkeypatch.setattr(ux, "send_message", send)
    monkeypatch.setattr(quick, "send_message", send)
    return db, sent


def _message(text, mid=None):
    msg = {"text": text, "chat": {"id": 10}}
    if mid is not None:
        msg["message_id"] = mid
        msg["date"] = int(datetime.now(tz=app.LOCAL_TZ).timestamp())
    return msg


def _buttons(markup):
    return [item for row in markup["keyboard"] for item in row]


def test_menu_e_protocolo_trocam_acoes_sem_duplicar_inicio(monkeypatch):
    db, sent = _setup(monkeypatch)
    run = lambda text: asyncio.run(ux.handle_message(db, "token", _message(text)))

    assert run("🏋️ Treino")
    assert ux.START in _buttons(sent[-1][1])
    assert ux.END not in _buttons(sent[-1][1])
    assert run(ux.START)
    assert run("🏋️ Treino")
    assert ux.START not in _buttons(sent[-1][1])
    assert ux.END in _buttons(sent[-1][1])
    assert ux.RESTART in _buttons(sent[-1][1])
    assert run(ux.START)
    assert db.conn.execute("SELECT active FROM protocol_mass_state").fetchone()[0] == 1


def test_fim_preserva_historico_e_reinicio_exige_confirmacao(monkeypatch):
    db, sent = _setup(monkeypatch)
    run = lambda text: asyncio.run(ux.handle_message(db, "token", _message(text)))
    run(ux.START)
    assert asyncio.run(quick.handle_message(db, "token", _message("Supino reto | 40 kg | 10 reps", 201)))
    assert db.count("protocol_mass_set_logs") == 1

    assert run(ux.END)
    assert db.conn.execute("SELECT active FROM protocol_mass_state").fetchone()[0] == 1
    assert run("ENCERRAR")
    status = db.conn.execute("SELECT active,finished_at FROM protocol_mass_state").fetchone()
    assert status["active"] == 0 and status["finished_at"]
    assert db.count("protocol_mass_set_logs") == 1
    assert run("🏋️ Treino")
    assert ux.START not in _buttons(sent[-1][1])
    assert ux.RESTART in _buttons(sent[-1][1])

    assert run(ux.RESTART)
    assert db.count("protocol_mass_set_logs") == 1
    assert run("❌ Cancelar ação")
    assert db.count("protocol_mass_set_logs") == 1
    assert run(ux.RESTART)
    assert run("APAGAR TREINOS")
    assert db.count("protocol_mass_set_logs") == 0
    assert db.conn.execute("SELECT active,current_week FROM protocol_mass_state").fetchone()[:] == (0, 1)


def test_semana_atual_e_proximas_sao_consulta_sem_mudar_protocolo(monkeypatch):
    db, sent = _setup(monkeypatch)
    run = lambda text: asyncio.run(ux.handle_message(db, "token", _message(text)))
    run(ux.START)
    assert run(ux.WEEK)
    assert "Supino reto" in sent[-1][0]
    assert "Segunda" in sent[-1][0]
    assert run(ux.NEXT)
    assert "Semana 2" in sent[-1][0]
    assert run("📆 Semana 2")
    assert "Supino inclinado" in sent[-1][0]
    assert "consulta, sem alterar" in sent[-1][0]
    assert db.conn.execute("SELECT current_week FROM protocol_mass_state").fetchone()[0] == 1


def test_registro_independente_e_idempotencia_real(monkeypatch):
    db, sent = _setup(monkeypatch)
    asyncio.run(ux.handle_message(db, "token", _message(ux.START)))

    first = _message("Supino reto | 40 kg | 10 reps", 301)
    second = _message("Supino reto | 45 kg | 8 reps", 302)
    assert asyncio.run(quick.handle_message(db, "token", first))
    assert asyncio.run(quick.handle_message(db, "token", first))
    assert db.count("protocol_mass_set_logs") == 1
    assert "Nenhuma duplicação" in sent[-1][0]
    assert asyncio.run(quick.handle_message(db, "token", second))
    assert db.count("protocol_mass_set_logs") == 2
    registered = db.conn.execute(
        "SELECT set_number,load,reps FROM protocol_mass_set_logs ORDER BY set_number"
    ).fetchall()
    assert [(r["set_number"], r["load"], r["reps"]) for r in registered] == [
        (1, "40 kg", "10 reps"), (2, "45 kg", "8 reps")
    ]
    assert asyncio.run(quick.handle_message(db, "token", _message("Agachamento | 40 kg | 10 reps", 303)))
    assert db.count("protocol_mass_set_logs") == 2


def test_registro_inativo_bloqueado_e_parser_estrito(monkeypatch):
    db, _ = _setup(monkeypatch)
    assert asyncio.run(quick.handle_message(db, "token", _message("Supino reto | 40 kg | 10 reps", 404)))
    assert db.count("protocol_mass_set_logs") == 0
    assert quick.parse_quick_series("Supino reto | pesado | 10 reps") is None
    assert quick.parse_quick_series("Supino reto | 20 kg | muitas reps") is None
    assert quick.parse_quick_series("Supino reto | 20 kg | 10 reps") is not None
