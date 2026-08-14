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
                skipped_at TEXT,
                skip_reason TEXT,
                UNIQUE(week, weekday)
            );

            CREATE TABLE IF NOT EXISTS protocol_mass_exercise_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week INTEGER NOT NULL,
                weekday TEXT NOT NULL,
                exercise_name TEXT NOT NULL,
                result TEXT,
                status TEXT NOT NULL DEFAULT 'feito',
                substituted_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(week, weekday, exercise_name)
            );
            """
        )
        conn.execute("INSERT OR IGNORE INTO protocol_mass_state (id, current_week, active) VALUES (1, 1, 0)")

        # Migração leve para bancos criados antes dos campos de falta.
        columns = {row[1] for row in conn.execute("PRAGMA table_info(protocol_mass_sessions)").fetchall()}
        if "skipped_at" not in columns:
            conn.execute("ALTER TABLE protocol_mass_sessions ADD COLUMN skipped_at TEXT")
        if "skip_reason" not in columns:
            conn.execute("ALTER TABLE protocol_mass_sessions ADD COLUMN skip_reason TEXT")


def get_state() -> sqlite3.Row:
    with _connect() as conn:
        return conn.execute("SELECT * FROM protocol_mass_state WHERE id = 1").fetchone()


def start_protocol() -> sqlite3.Row:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        state = conn.execute("SELECT * FROM protocol_mass_state WHERE id = 1").fetchone()
        if not state["active"]:
            if state["finished_at"]:
                reset_protocol(conn=conn)
                conn.execute(
                    "UPDATE protocol_mass_state SET active = 1, started_at = ?, finished_at = NULL WHERE id = 1",
                    (now,),
                )
            else:
                conn.execute(
                    "UPDATE protocol_mass_state SET active = 1, started_at = COALESCE(started_at, ?) WHERE id = 1",
                    (now,),
                )
        return conn.execute("SELECT * FROM protocol_mass_state WHERE id = 1").fetchone()


def reset_protocol(conn: sqlite3.Connection | None = None) -> None:
    own_conn = conn is None
    db = conn or _connect()
    try:
        db.execute("DELETE FROM protocol_mass_exercise_logs")
        db.execute("DELETE FROM protocol_mass_sessions")
        db.execute(
            "UPDATE protocol_mass_state SET current_week = 1, active = 0, started_at = NULL, finished_at = NULL WHERE id = 1"
        )
        if own_conn:
            db.commit()
    finally:
        if own_conn:
            db.close()


def begin_today(week: int, weekday: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO protocol_mass_sessions (week, weekday, training_date, started_at, skipped_at, skip_reason)
            VALUES (?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(week, weekday) DO UPDATE SET
                training_date = excluded.training_date,
                started_at = COALESCE(protocol_mass_sessions.started_at, excluded.started_at),
                skipped_at = NULL,
                skip_reason = NULL
            """,
            (week, weekday, date.today().isoformat(), now),
        )


def skip_today(week: int, weekday: str, reason: str | None = None) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO protocol_mass_sessions
                (week, weekday, training_date, started_at, completed_at, skipped_at, skip_reason)
            VALUES (?, ?, ?, NULL, NULL, ?, ?)
            ON CONFLICT(week, weekday) DO UPDATE SET
                training_date = excluded.training_date,
                completed_at = NULL,
                skipped_at = excluded.skipped_at,
                skip_reason = excluded.skip_reason
            """,
            (week, weekday, date.today().isoformat(), now, reason),
        )


def complete_today(week: int, weekday: str) -> tuple[int, int, bool]:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO protocol_mass_sessions
                (week, weekday, training_date, started_at, completed_at, skipped_at, skip_reason)
            VALUES (?, ?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(week, weekday) DO UPDATE SET
                completed_at = excluded.completed_at,
                skipped_at = NULL,
                skip_reason = NULL
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
                conn.execute("UPDATE protocol_mass_state SET active = 0, finished_at = ? WHERE id = 1", (now,))
        return int(completed), min(week + 1, 12), advanced


def log_exercise(
    week: int,
    weekday: str,
    exercise_name: str,
    result: str | None = None,
    status: str = "feito",
    substituted_by: str | None = None,
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO protocol_mass_exercise_logs
                (week, weekday, exercise_name, result, status, substituted_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(week, weekday, exercise_name) DO UPDATE SET
                result = excluded.result,
                status = excluded.status,
                substituted_by = excluded.substituted_by,
                updated_at = excluded.updated_at
            """,
            (week, weekday, exercise_name, result, status, substituted_by, now, now),
        )


def exercise_logs(week: int, weekday: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            """
            SELECT exercise_name, result, status, substituted_by
            FROM protocol_mass_exercise_logs
            WHERE week = ? AND weekday = ?
            ORDER BY id
            """,
            (week, weekday),
        ).fetchall()


def week_progress(week: int) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            """
            SELECT weekday, training_date, started_at, completed_at, skipped_at, skip_reason
            FROM protocol_mass_sessions WHERE week = ? ORDER BY id
            """,
            (week,),
        ).fetchall()


def completed_days(week: int) -> set[str]:
    return {row["weekday"] for row in week_progress(week) if row["completed_at"]}


def skipped_days(week: int) -> dict[str, str | None]:
    return {row["weekday"]: row["skip_reason"] for row in week_progress(week) if row["skipped_at"]}
