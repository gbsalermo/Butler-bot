import sqlite3
from datetime import date, datetime
from pathlib import Path

from src.config import DATABASE_PATH


def _connect() -> sqlite3.Connection:
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_protocol_mass_tables() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS protocol_mass_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_week INTEGER NOT NULL DEFAULT 1,
                active INTEGER NOT NULL DEFAULT 0,
                started_at TEXT,
                finished_at TEXT
            );

            CREATE TABLE IF NOT EXISTS protocol_mass_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week INTEGER NOT NULL,
                weekday TEXT NOT NULL,
                training_date TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                UNIQUE(week, weekday)
            );
            """
        )
        conn.execute("INSERT OR IGNORE INTO protocol_mass_state (id, current_week, active) VALUES (1, 1, 0)")


def get_state() -> sqlite3.Row:
    with _connect() as conn:
        return conn.execute("SELECT * FROM protocol_mass_state WHERE id = 1").fetchone()


def start_protocol() -> sqlite3.Row:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        state = conn.execute("SELECT * FROM protocol_mass_state WHERE id = 1").fetchone()
        if not state["active"]:
            # Se o protocolo já foi totalmente concluído, um novo início recomeça pela semana 1.
            if state["finished_at"]:
                conn.execute("DELETE FROM protocol_mass_sessions")
                conn.execute(
                    "UPDATE protocol_mass_state SET current_week = 1, active = 1, started_at = ?, finished_at = NULL WHERE id = 1",
                    (now,),
                )
            else:
                conn.execute(
                    "UPDATE protocol_mass_state SET active = 1, started_at = COALESCE(started_at, ?) WHERE id = 1",
                    (now,),
                )
        return conn.execute("SELECT * FROM protocol_mass_state WHERE id = 1").fetchone()


def begin_today(week: int, weekday: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO protocol_mass_sessions (week, weekday, training_date, started_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(week, weekday) DO UPDATE SET
                training_date = excluded.training_date,
                started_at = COALESCE(protocol_mass_sessions.started_at, excluded.started_at)
            """,
            (week, weekday, date.today().isoformat(), now),
        )


def complete_today(week: int, weekday: str) -> tuple[int, int, bool]:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO protocol_mass_sessions (week, weekday, training_date, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(week, weekday) DO UPDATE SET completed_at = excluded.completed_at
            """,
            (week, weekday, date.today().isoformat(), now, now),
        )
        completed = conn.execute(
            "SELECT COUNT(*) FROM protocol_mass_sessions WHERE week = ? AND completed_at IS NOT NULL",
            (week,),
        ).fetchone()[0]
        advanced = False
        if completed >= 6:
            if week < 12:
                conn.execute("UPDATE protocol_mass_state SET current_week = ? WHERE id = 1", (week + 1,))
                advanced = True
            else:
                conn.execute(
                    "UPDATE protocol_mass_state SET active = 0, finished_at = ? WHERE id = 1",
                    (now,),
                )
        return int(completed), min(week + 1, 12), advanced


def week_progress(week: int) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT weekday, training_date, started_at, completed_at FROM protocol_mass_sessions WHERE week = ? ORDER BY id",
            (week,),
        ).fetchall()


def completed_days(week: int) -> set[str]:
    return {row["weekday"] for row in week_progress(week) if row["completed_at"]}
