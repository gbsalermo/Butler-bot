import sqlite3
from datetime import datetime

from src.user_scope import resolve_database_path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(resolve_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_assistant_state() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS assistant_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                day_off INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS routines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                time_hhmm TEXT,
                weekdays TEXT,
                reminder_minutes INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS routine_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                routine_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'feito',
                created_at TEXT NOT NULL,
                FOREIGN KEY(routine_id) REFERENCES routines(id) ON DELETE CASCADE,
                UNIQUE(routine_id, log_date)
            );

            CREATE TABLE IF NOT EXISTS goal_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                note TEXT,
                log_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE CASCADE
            );
            """
        )
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            "INSERT OR IGNORE INTO assistant_state (id, day_off, updated_at) VALUES (1, 0, ?)",
            (now,),
        )


def is_day_off() -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT day_off FROM assistant_state WHERE id = 1").fetchone()
        return bool(row and row["day_off"])


def set_day_off(enabled: bool) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE assistant_state SET day_off = ?, updated_at = ? WHERE id = 1",
            (1 if enabled else 0, datetime.now().isoformat(timespec="seconds")),
        )


def add_routine(name: str, category: str, time_hhmm: str | None, weekdays: str | None,
                reminder_minutes: int = 0) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO routines (name, category, time_hhmm, weekdays, reminder_minutes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name.strip(), category.strip(), time_hhmm, weekdays, reminder_minutes,
             datetime.now().isoformat(timespec="seconds")),
        )
        return int(cur.lastrowid)


def list_routines(active_only: bool = True) -> list[sqlite3.Row]:
    where = "WHERE active = 1" if active_only else ""
    with _connect() as conn:
        return conn.execute(
            f"SELECT id, name, category, time_hhmm, weekdays, reminder_minutes, active FROM routines {where} ORDER BY time_hhmm, id"
        ).fetchall()


def complete_routine(routine_id: int, log_date: str) -> bool:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO routine_logs (routine_id, log_date, status, created_at) VALUES (?, ?, 'feito', ?)",
            (routine_id, log_date, datetime.now().isoformat(timespec="seconds")),
        )
        return True


def add_goal_progress(goal_id: int, amount: float, note: str | None, log_date: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO goal_progress (goal_id, amount, note, log_date, created_at) VALUES (?, ?, ?, ?, ?)",
            (goal_id, amount, note, log_date, datetime.now().isoformat(timespec="seconds")),
        )
        return int(cur.lastrowid)


def goal_progress_totals() -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            """
            SELECT g.id, g.name, g.category, g.target_value, g.target_unit, g.period,
                   COALESCE(SUM(gp.amount), 0) AS progress
            FROM goals g
            LEFT JOIN goal_progress gp ON gp.goal_id = g.id
            WHERE g.active = 1
            GROUP BY g.id
            ORDER BY g.category, g.name
            """
        ).fetchall()
