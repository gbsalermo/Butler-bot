import os
import sqlite3
from contextvars import ContextVar
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes, TypeHandler

from src.config import DATABASE_PATH

_CURRENT_CHAT_ID: ContextVar[int | None] = ContextVar("butler_chat_id", default=None)
_INITIALIZED: set[int] = set()


def multiuser_enabled() -> bool:
    return os.getenv("BUTLER_MULTIUSER", "0").strip().lower() in {"1", "true", "yes", "sim"}


def current_chat_id() -> int | None:
    return _CURRENT_CHAT_ID.get()


def set_current_chat_id(chat_id: int | None) -> None:
    _CURRENT_CHAT_ID.set(chat_id)


def resolve_database_path() -> Path:
    """Retorna o banco correspondente ao chat atual.

    Butler pessoal: mantém DATABASE_PATH exatamente como antes.
    Butler genérico/multiusuário: cada chat privado recebe um SQLite próprio.
    """
    base = Path(DATABASE_PATH)
    if not multiuser_enabled():
        return base

    chat_id = current_chat_id()
    if chat_id is None:
        return base

    users_dir = base.parent / f"{base.stem}_users"
    users_dir.mkdir(parents=True, exist_ok=True)
    return users_dir / f"{chat_id}.db"


def registry_path() -> Path:
    base = Path(DATABASE_PATH)
    return base.parent / f"{base.stem}_registry.db"


def _register_chat(chat_id: int) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS registered_chats (
                chat_id INTEGER PRIMARY KEY,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("INSERT OR IGNORE INTO registered_chats (chat_id) VALUES (?)", (chat_id,))


def registered_chat_ids() -> list[int]:
    path = registry_path()
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        try:
            rows = conn.execute(
                "SELECT chat_id FROM registered_chats WHERE active = 1 ORDER BY chat_id"
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    return [int(row[0]) for row in rows]


def initialize_current_user_storage() -> None:
    """Cria/migra as tabelas do chat atual na primeira interação do processo."""
    chat_id = current_chat_id()
    if not multiuser_enabled() or chat_id is None or chat_id in _INITIALIZED:
        return

    from src.assistant_state import init_assistant_state
    from src.daily_store import init_daily_store
    from src.database import init_database
    from src.home_store import init_home_tables

    init_database()
    init_daily_store()
    init_home_tables()
    init_assistant_state()
    _INITIALIZED.add(chat_id)


async def establish_user_scope(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    chat_id = int(update.effective_chat.id)
    set_current_chat_id(chat_id)
    if multiuser_enabled():
        _register_chat(chat_id)
        initialize_current_user_storage()


def register_user_scope(application) -> None:
    # TypeHandler cobre mensagens e callbacks. O group muito baixo garante que o
    # banco do chat esteja selecionado antes de qualquer regra de negócio.
    application.add_handler(TypeHandler(Update, establish_user_scope), group=-100)
