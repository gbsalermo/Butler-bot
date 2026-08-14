import sqlite3
from datetime import datetime
from pathlib import Path

from src.config import DATABASE_PATH


def _connect() -> sqlite3.Connection:
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_home_tables() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS grocery_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                quantity TEXT,
                note TEXT,
                missing INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                target_value REAL,
                target_unit TEXT,
                period TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workout_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weekday TEXT NOT NULL UNIQUE,
                focus TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workout_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_day_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                load TEXT,
                sets INTEGER,
                reps TEXT,
                position INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(workout_day_id) REFERENCES workout_days(id) ON DELETE CASCADE
            );
            """
        )


def add_grocery_item(name: str, quantity: str | None = None, note: str | None = None) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO grocery_items (name, quantity, note, missing, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                quantity = excluded.quantity,
                note = excluded.note,
                missing = 1,
                updated_at = excluded.updated_at
            """,
            (name.strip(), quantity, note, now, now),
        )


def list_missing_groceries() -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT id, name, quantity, note FROM grocery_items WHERE missing = 1 ORDER BY name"
        ).fetchall()


def mark_grocery_bought(item_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE grocery_items SET missing = 0, updated_at = ? WHERE id = ? AND missing = 1",
            (datetime.now().isoformat(timespec="seconds"), item_id),
        )
        return cur.rowcount > 0


def add_goal(name: str, category: str, target_value: float | None, target_unit: str | None, period: str | None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO goals (name, category, target_value, target_unit, period, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name.strip(), category.strip(), target_value, target_unit, period, datetime.now().isoformat(timespec="seconds")),
        )


def list_goals() -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT id, name, category, target_value, target_unit, period FROM goals WHERE active = 1 ORDER BY category, name"
        ).fetchall()


def upsert_workout_day(weekday: str, focus: str) -> int:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO workout_days (weekday, focus) VALUES (?, ?) ON CONFLICT(weekday) DO UPDATE SET focus = excluded.focus",
            (weekday, focus.strip()),
        )
        row = conn.execute("SELECT id FROM workout_days WHERE weekday = ?", (weekday,)).fetchone()
        return int(row["id"])


def add_workout_exercise(weekday: str, focus: str, name: str, load: str | None, sets: int | None, reps: str | None) -> None:
    day_id = upsert_workout_day(weekday, focus)
    with _connect() as conn:
        position = conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM workout_exercises WHERE workout_day_id = ?",
            (day_id,),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO workout_exercises (workout_day_id, name, load, sets, reps, position) VALUES (?, ?, ?, ?, ?, ?)",
            (day_id, name.strip(), load, sets, reps, position),
        )


def list_workout() -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            """
            SELECT wd.weekday, wd.focus, we.id, we.name, we.load, we.sets, we.reps
            FROM workout_days wd
            LEFT JOIN workout_exercises we ON we.workout_day_id = wd.id
            ORDER BY CASE wd.weekday
                WHEN 'segunda-feira' THEN 1 WHEN 'terça-feira' THEN 2 WHEN 'quarta-feira' THEN 3
                WHEN 'quinta-feira' THEN 4 WHEN 'sexta-feira' THEN 5 WHEN 'sábado' THEN 6 WHEN 'domingo' THEN 7 ELSE 8 END,
                we.position
            """
        ).fetchall()
