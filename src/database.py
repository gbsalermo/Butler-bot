import sqlite3
from datetime import datetime
from typing import Iterable

from src.user_scope import resolve_database_path


DEFAULT_SUBJECTS = [
    {"name": "Álgebra Linear I", "sessions": [("terça-feira", "10:00", "12:00", "PAV III, Sala 10"), ("quinta-feira", "10:00", "12:00", "PAV III, Sala 10")]},
    {"name": "Física II", "sessions": [("segunda-feira", "10:00", "12:00", "PAV III, Sala 07"), ("quarta-feira", "10:00", "12:00", "PAV III, Sala 07")]},
    {"name": "Laboratório de Sistemas Digitais I", "sessions": [("segunda-feira", "14:00", "16:00", "PAV Eng., Sala D6")]},
    {"name": "Princípios de Eletrônica Analógica", "sessions": [("terça-feira", "08:00", "10:00", "PAV I, Sala 104"), ("quinta-feira", "08:00", "10:00", "PAV I, Sala 104")]},
    {"name": "Sistemas Digitais I", "sessions": [("segunda-feira", "08:00", "10:00", "PAV I, Sala 11"), ("quarta-feira", "08:00", "10:00", "PAV I, Sala 114")]},
]

LEGACY_TIME_NORMALIZATION = {
    "07:10": "07:00", "08:01": "08:00", "08:50": "09:00", "08:51": "09:00",
    "09:40": "10:00", "10:50": "11:00", "10:51": "11:00", "11:40": "12:00",
    "11:41": "12:00", "12:30": "13:00", "13:10": "13:00", "14:01": "14:00",
    "14:50": "15:00", "14:51": "15:00", "15:40": "16:00", "16:50": "17:00",
    "16:51": "17:00", "17:40": "18:00", "17:41": "18:00", "18:30": "19:00",
    "18:05": "18:00", "18:50": "19:00", "18:51": "19:00", "19:35": "20:00",
    "19:36": "20:00", "20:20": "21:00", "20:30": "21:00", "21:15": "22:00",
    "21:16": "22:00",
}


def _connect() -> sqlite3.Connection:
    db_path = resolve_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _normalize_legacy_class_times(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id, start_time, end_time FROM class_sessions").fetchall()
    for row in rows:
        original_start = row["start_time"]
        original_end = row["end_time"]
        start = LEGACY_TIME_NORMALIZATION.get(original_start, original_start)
        end = LEGACY_TIME_NORMALIZATION.get(original_end, original_end)
        if original_end == "22:00" and original_start in {"20:30", "21:16"}:
            end = "23:00"
        if start != original_start or end != original_end:
            conn.execute(
                "UPDATE class_sessions SET start_time = ?, end_time = ? WHERE id = ?",
                (start, end, row["id"]),
            )


def init_database() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_chat_id INTEGER NOT NULL UNIQUE,
                telegram_user_id INTEGER,
                first_name TEXT,
                username TEXT,
                preferred_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS class_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                weekday TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT,
                FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                UNIQUE(subject_id, weekday, start_time, end_time, location)
            );
            """
        )
        _ensure_column(conn, "users", "preferred_name", "TEXT")
        _normalize_legacy_class_times(conn)


def upsert_user(chat_id: int, user_id: int | None, first_name: str | None, username: str | None) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_chat_id, telegram_user_id, first_name, username, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_chat_id) DO UPDATE SET
                telegram_user_id = excluded.telegram_user_id,
                first_name = excluded.first_name,
                username = excluded.username,
                updated_at = excluded.updated_at
            """,
            (chat_id, user_id, first_name, username, now, now),
        )


def get_user(chat_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute("SELECT * FROM users WHERE telegram_chat_id = ?", (chat_id,)).fetchone()


def set_preferred_name(chat_id: int, preferred_name: str) -> bool:
    value = preferred_name.strip()
    if not value:
        return False
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE users SET preferred_name = ?, updated_at = ? WHERE telegram_chat_id = ?",
            (value, datetime.now().isoformat(timespec="seconds"), chat_id),
        )
        return cur.rowcount > 0


def preferred_name(chat_id: int, fallback: str = "chefe") -> str:
    row = get_user(chat_id)
    if row and row["preferred_name"]:
        return str(row["preferred_name"])
    return fallback


def add_subject(name: str, sessions: Iterable[tuple[str, str, str, str]]) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        cursor = conn.execute("INSERT INTO subjects (name, created_at) VALUES (?, ?)", (name.strip(), now))
        subject_id = int(cursor.lastrowid)
        conn.executemany(
            "INSERT INTO class_sessions (subject_id, weekday, start_time, end_time, location) VALUES (?, ?, ?, ?, ?)",
            [(subject_id, weekday, start_time, end_time, (location or "").strip()) for weekday, start_time, end_time, location in sessions],
        )
        return subject_id


def upsert_subject_schedule(name: str, sessions: Iterable[tuple[str, str, str, str]]) -> int:
    sessions_list = list(sessions)
    existing = get_subject_by_name(name)
    if existing:
        replace_subject_sessions(name, sessions_list)
        with _connect() as conn:
            conn.execute("UPDATE subjects SET active = 1 WHERE id = ?", (existing["id"],))
        return int(existing["id"])
    return add_subject(name, sessions_list)


def seed_default_schedule() -> None:
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        if count > 0:
            return
    for subject in DEFAULT_SUBJECTS:
        add_subject(subject["name"], subject["sessions"])


def list_subjects(include_locked: bool = False) -> list[sqlite3.Row]:
    where = "" if include_locked else "WHERE s.active = 1"
    with _connect() as conn:
        return conn.execute(
            f"""
            SELECT s.id, s.name, s.active, cs.weekday, cs.start_time, cs.end_time, cs.location
            FROM subjects s
            LEFT JOIN class_sessions cs ON cs.subject_id = s.id
            {where}
            ORDER BY s.active DESC, s.name, cs.start_time, cs.weekday
            """
        ).fetchall()


def list_subject_names(active_only: bool = True) -> list[str]:
    where = "WHERE active = 1" if active_only else ""
    with _connect() as conn:
        rows = conn.execute(f"SELECT name FROM subjects {where} ORDER BY name").fetchall()
        return [row["name"] for row in rows]


def get_subject_by_name(name: str) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute("SELECT id, name, active FROM subjects WHERE name = ?", (name,)).fetchone()


def delete_subject(name: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM subjects WHERE name = ?", (name,))
        return cursor.rowcount > 0


def lock_subject(name: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute("UPDATE subjects SET active = 0 WHERE name = ? AND active = 1", (name,))
        return cursor.rowcount > 0


def update_subject_name(old_name: str, new_name: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute("UPDATE subjects SET name = ? WHERE name = ?", (new_name.strip(), old_name))
        return cursor.rowcount > 0


def replace_subject_sessions(name: str, sessions: Iterable[tuple[str, str, str, str]]) -> bool:
    subject = get_subject_by_name(name)
    if subject is None:
        return False
    subject_id = subject["id"]
    with _connect() as conn:
        conn.execute("DELETE FROM class_sessions WHERE subject_id = ?", (subject_id,))
        conn.executemany(
            "INSERT INTO class_sessions (subject_id, weekday, start_time, end_time, location) VALUES (?, ?, ?, ?, ?)",
            [(subject_id, weekday, start_time, end_time, (location or "").strip()) for weekday, start_time, end_time, location in sessions],
        )
    return True


def update_subject_location(name: str, location: str) -> bool:
    subject = get_subject_by_name(name)
    if subject is None:
        return False
    with _connect() as conn:
        cursor = conn.execute("UPDATE class_sessions SET location = ? WHERE subject_id = ?", (location.strip(), subject["id"]))
        return cursor.rowcount > 0
