import sqlite3
from datetime import datetime

from src.user_scope import resolve_database_path

VALID_KINDS = {"tarefa", "compromisso"}
_UNSET = object()


def _connect() -> sqlite3.Connection:
    db_path = resolve_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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
        _ensure_column(conn, "daily_items", "snoozed_until", "TEXT")
        conn.execute("UPDATE daily_items SET kind = 'tarefa' WHERE kind = 'pendencia'")


def add_item(kind: str, title: str, due_date: str | None = None, due_time: str | None = None,
             details: str | None = None, reminder_minutes: int = 10) -> int:
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
                   reminder_minutes, status, created_at, completed_at, snoozed_until
            FROM daily_items
            {where}
            ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date,
                     CASE WHEN due_time IS NULL THEN 1 ELSE 0 END, due_time, id
            """,
            params,
        ).fetchall()


def get_item(item_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute("SELECT * FROM daily_items WHERE id = ?", (item_id,)).fetchone()


def complete_item(item_id: int) -> bool:
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE daily_items SET status = 'concluido', completed_at = ?, snoozed_until = NULL WHERE id = ? AND status = 'pendente'",
            (now, item_id),
        )
        return cur.rowcount > 0


def delete_item(item_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM daily_items WHERE id = ?", (item_id,))
        return cur.rowcount > 0


def update_item(item_id: int, *, title=_UNSET, due_date=_UNSET, due_time=_UNSET,
                details=_UNSET, reminder_minutes=_UNSET) -> bool:
    current = get_item(item_id)
    if current is None:
        return False
    with _connect() as conn:
        cur = conn.execute(
            """
            UPDATE daily_items
            SET title = ?, due_date = ?, due_time = ?, details = ?, reminder_minutes = ?, snoozed_until = NULL
            WHERE id = ?
            """,
            (
                current["title"] if title is _UNSET else title,
                current["due_date"] if due_date is _UNSET else due_date,
                current["due_time"] if due_time is _UNSET else due_time,
                current["details"] if details is _UNSET else details,
                current["reminder_minutes"] if reminder_minutes is _UNSET else reminder_minutes,
                item_id,
            ),
        )
        return cur.rowcount > 0


def snooze_item(item_id: int, until_iso: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE daily_items SET snoozed_until = ? WHERE id = ? AND status = 'pendente'",
            (until_iso, item_id),
        )
        return cur.rowcount > 0


def clear_snooze(item_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE daily_items SET snoozed_until = NULL WHERE id = ?", (item_id,))
