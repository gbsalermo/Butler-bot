"""Diagnósticos administrativos restritos ao proprietário do Butler."""

import re
import unicodedata

import app
from owner_profile import is_owner
from telegram_api import send_message

USER_STATUS_ALIASES = {
    "status usuarios",
    "status de usuarios",
    "usuarios cadastrados",
    "listar usuarios",
    "quantos usuarios",
    "quantos ids",
}
USER_LIST_LIMIT = 30


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("_", " ")
    value = re.sub(r"[^a-z0-9/ ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _is_user_status_command(text):
    normalized = _norm(text)
    if normalized.startswith("/"):
        normalized = normalized[1:].strip()
    return normalized in USER_STATUS_ALIASES


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


def _display_name(row):
    preferred = (_row(row, "preferred_name") or "").strip()
    first = (_row(row, "first_name") or "").strip()
    username = (_row(row, "username") or "").strip()
    if preferred:
        return preferred
    if first:
        return first
    if username:
        return f"@{username}"
    return "sem nome"


def _created_date(value):
    value = str(value or "").strip()
    if len(value) >= 10 and value[4:5] == "-" and value[7:8] == "-":
        return f"{value[8:10]}/{value[5:7]}/{value[0:4]}"
    return value or "data desconhecida"


async def _user_status_text(db):
    count_row = await db.prepare("SELECT COUNT(*) total FROM users").first()
    total = int(_row(count_row, "total", 0) or 0)
    users = await _rows(
        db.prepare(
            "SELECT id,telegram_chat_id,preferred_name,first_name,username,is_owner,created_at "
            "FROM users ORDER BY id ASC LIMIT ?"
        ).bind(USER_LIST_LIMIT)
    )

    out = [f"👥 Usuários cadastrados: {total}"]
    if not users:
        out.append("\nNenhum usuário cadastrado.")
        return "\n".join(out)

    out.append("\nIDs registrados:")
    for row in users:
        owner_mark = " 👑" if int(_row(row, "is_owner", 0) or 0) else ""
        out.append(
            f"• #{_row(row, 'id')} | chat {_row(row, 'telegram_chat_id')} | "
            f"{_display_name(row)}{owner_mark} | {_created_date(_row(row, 'created_at'))}"
        )

    remaining = total - len(users)
    if remaining > 0:
        out.append(f"\n… e mais {remaining} usuário(s).")
    return "\n".join(out)


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    if not _is_user_status_command(text):
        return False

    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    chat_id = int(chat_id)

    # O gate usa a identidade autoritativa do proprietário, não um parâmetro
    # vindo da mensagem nem apenas a coluna mutável do banco.
    if not is_owner(chat_id):
        await send_message(token, chat_id, "🔒 Esse diagnóstico é administrativo.")
        return True

    await send_message(
        token,
        chat_id,
        await _user_status_text(db),
        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
    )
    return True
