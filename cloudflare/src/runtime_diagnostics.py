"""Diagnóstico mínimo e persistente de falhas do runtime.

Não substitui os logs da Cloudflare. Serve para impedir que exceções no Worker
sejam totalmente invisíveis ao proprietário e para expor um resumo seguro via
``/status runtime``.
"""

from __future__ import annotations

from owner_profile import is_owner
from telegram_api import send_message

_SCHEMA_READY = False


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


async def _rows(stmt):
    result = await stmt.all()
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


async def ensure_schema(db):
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS runtime_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL,
            error_type TEXT NOT NULL,
            error_message TEXT,
            chat_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_runtime_errors_created "
        "ON runtime_errors(created_at DESC, id DESC)"
    ).run()
    _SCHEMA_READY = True


async def record_error(db, scope, exc, *, chat_id=None):
    """Registra erro sem persistir texto da conversa do usuário."""
    try:
        await ensure_schema(db)
        await db.prepare(
            "INSERT INTO runtime_errors(scope,error_type,error_message,chat_id) VALUES(?,?,?,?)"
        ).bind(
            str(scope)[:120],
            type(exc).__name__[:120],
            str(exc)[:600],
            int(chat_id) if chat_id is not None else None,
        ).run()
    except Exception as log_exc:
        print(
            f"[runtime-diagnostics] log-failed type={type(log_exc).__name__} "
            f"message={str(log_exc)[:300]}"
        )


async def _table_exists(db, name):
    try:
        row = await db.prepare(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        ).bind(name).first()
        return bool(row)
    except Exception:
        return False


async def _latest_tick(db):
    for sql in (
        "SELECT created_at FROM attendance_scheduler_ticks ORDER BY id DESC LIMIT 1",
        "SELECT tick_at AS created_at FROM attendance_scheduler_ticks ORDER BY id DESC LIMIT 1",
    ):
        try:
            row = await db.prepare(sql).first()
            if row:
                return _row(row, "created_at")
        except Exception:
            continue
    return None


def _lazy_schema_status(exists):
    return "✅" if exists else "ℹ️ ainda não inicializado"


async def runtime_status_text(db):
    try:
        await db.prepare("SELECT 1").first()
        db_ok = True
    except Exception:
        db_ok = False

    quick = await _table_exists(db, "quick_timers") if db_ok else False
    study = await _table_exists(db, "study_sessions") if db_ok else False
    errors_table = await _table_exists(db, "runtime_errors") if db_ok else False
    tick = await _latest_tick(db) if db_ok else None

    lines = [
        "🩺 Status de runtime do Butler",
        "",
        f"D1: {'✅ acessível' if db_ok else '❌ indisponível'}",
        f"quick_timers: {_lazy_schema_status(quick)}",
        f"study_sessions: {_lazy_schema_status(study)}",
        f"heartbeat presença: {tick or 'sem registro legível'}",
    ]

    if db_ok and errors_table:
        try:
            errors = await _rows(
                db.prepare(
                    "SELECT scope,error_type,error_message,created_at FROM runtime_errors "
                    "ORDER BY id DESC LIMIT 5"
                )
            )
        except Exception:
            errors = []
        if errors:
            lines.append("\nÚltimos erros capturados (histórico; confira o horário):")
            for item in errors:
                message = (_row(item, "error_message") or "")[:180]
                lines.append(
                    f"• {_row(item,'created_at')} | {_row(item,'scope')} | "
                    f"{_row(item,'error_type')}: {message}"
                )
        else:
            lines.append("\nErros persistidos: nenhum até agora.")
    else:
        lines.append("\nErros persistidos: tabela ainda não criada.")

    return "\n".join(lines)


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip().lower()
    if text not in {"/status runtime", "/status_runtime", "status runtime"}:
        return False
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    if not is_owner(int(chat_id)):
        return False
    await send_message(token, int(chat_id), await runtime_status_text(db))
    return True
