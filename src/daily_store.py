import sqlite3
from datetime import datetime
from pathlib import Path

from src.config import DATABASE_PATH

VALID_KINDS = {"tarefa", "compromisso", "pendencia"}


def _connect() -> sqlite3.Connection:
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_daily_store() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS daily_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT,
                due_date TEXT,
                due_time TEXT,
                reminder_minutes INTEGER NOT NULL DEFAULT 10,
                status TEXT NOT NULL DEFAULT 'pendente',
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_daily_items_kind_status
                ON daily_items(kind, status);
            CREATE INDEX IF NOT EXISTS idx_daily_items_due
                ON daily_items(due_date, due_time, status);
            """
        )


def add_item(
    kind: str,
    title: str,
    due_date: str | None = None,
    due_time: str | None = None,
    details: str | None = None,
    reminder_minutes: int = 10,
) -> int:
    if kind not in VALID_KINDS:
        raise ValueError("Tipo de item inválido")
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO daily_items
                (kind, title, details, due_date, due_time, reminder_minutes, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?)
            """,
            (kind, title.strip(), details, due_date, due_time, reminder_minutes, now),
        )
        return int(cur.lastrowid)


def list_items(kind: str | None = None, only_pending: bool = True) -> list[sqlite3.Row]:
    clauses = []
    params: list[object] = []
    if kind:
        clauses.append("kind = ?")
        params.append(kind)
    if only_pending:
        clauses.append("status = 'pendente'")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with _connect() as conn:
        return conn.execute(
            f"""
            SELECT id, kind, title, details, due_date, due_time,
                   reminder_minutes, status, created_at, completed_at
            FROM daily_items
            {where}
            ORDER BY
                CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                due_date,
                CASE WHEN due_time IS NULL THEN 1 ELSE 0 END,
                due_time,
                id
            """,
            params,
        ).fetchall()


def complete_item(item_id: int) -> bool:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            """
            UPDATE daily_items
            SET status = 'concluido', completed_at = ?
            WHERE id = ? AND status = 'pendente'
            """,
            (now, item_id),
        )
        return cur.rowcount > 0


def delete_item(item_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM daily_items WHERE id = ?", (item_id,))
        return cur.rowcount > 0


def pending_due_items(date_iso: str, time_hhmm: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            """
            SELECT * FROM daily_items
            WHERE status = 'pendente'
              AND due_date = ?
              AND due_time IS NOT NULL
            ORDER BY due_time, id
            """,
            (date_iso,),
        ).fetchall()
