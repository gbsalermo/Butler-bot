import sqlite3
from datetime import datetime
from src.user_scope import resolve_database_path


def _connect():
    conn = sqlite3.connect(resolve_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_natural_tables():
    with _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS natural_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            reference_id INTEGER,
            detail TEXT,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_natural_events_type ON natural_events(event_type, created_at)")


def record_event(event_type: str, reference_id: int | None = None, detail: str | None = None) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO natural_events(event_type, reference_id, detail, created_at) VALUES (?, ?, ?, ?)",
            (event_type, reference_id, detail, datetime.now().isoformat(timespec="seconds")),
        )
        return int(cur.lastrowid)


def event_count(event_type: str) -> int:
    with _connect() as conn:
        try:
            return int(conn.execute("SELECT COUNT(*) FROM natural_events WHERE event_type = ?", (event_type,)).fetchone()[0])
        except sqlite3.OperationalError:
            return 0
