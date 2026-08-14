import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from src.config import DATABASE_PATH


DEFAULT_SUBJECTS = [
    {
        "name": "Álgebra Linear I",
        "sessions": [
            ("terça-feira", "10:00", "11:40", "PAV III, Sala 10"),
            ("quinta-feira", "10:00", "11:40", "PAV III, Sala 10"),
        ],
    },
    {
        "name": "Física II",
        "sessions": [
            ("segunda-feira", "10:00", "11:40", "PAV III, Sala 07"),
            ("quarta-feira", "10:00", "11:40", "PAV III, Sala 07"),
        ],
    },
    {
        "name": "Laboratório de Sistemas Digitais I",
        "sessions": [
            ("segunda-feira", "14:00", "16:00", "PAV Eng., Sala D6"),
        ],
    },
    {
        "name": "Princípios de Eletrônica Analógica",
        "sessions": [
            ("terça-feira", "08:01", "09:40", "PAV I, Sala 104"),
            ("quinta-feira", "08:01", "09:40", "PAV I, Sala 104"),
        ],
    },
    {
        "name": "Sistemas Digitais I",
        "sessions": [
            ("segunda-feira", "08:01", "09:40", "PAV I, Sala 11"),
            ("quarta-feira", "08:01", "09:40", "PAV I, Sala 114"),
        ],
    },
]


def _connect() -> sqlite3.Connection:
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


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


def add_subject(name: str, sessions: Iterable[tuple[str, str, str, str]]) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO subjects (name, created_at) VALUES (?, ?)",
            (name.strip(), now),
        )
        subject_id = int(cursor.lastrowid)
        conn.executemany(
            """
            INSERT INTO class_sessions (subject_id, weekday, start_time, end_time, location)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (subject_id, weekday, start_time, end_time, location.strip())
                for weekday, start_time, end_time, location in sessions
            ],
        )
        return subject_id


def seed_default_schedule() -> None:
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        if count > 0:
            return

    for subject in DEFAULT_SUBJECTS:
        add_subject(subject["name"], subject["sessions"])


def list_subjects() -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            """
            SELECT
                s.id,
                s.name,
                cs.weekday,
                cs.start_time,
                cs.end_time,
                cs.location
            FROM subjects s
            LEFT JOIN class_sessions cs ON cs.subject_id = s.id
            WHERE s.active = 1
            ORDER BY s.name, cs.start_time, cs.weekday
            """
        ).fetchall()
