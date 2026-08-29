"""Diagnósticos e ações administrativas restritos ao proprietário do Butler."""

import re
import unicodedata

import app
from owner_profile import is_owner
from telegram_api import delivery_ok, send_message

USER_STATUS_ALIASES = {
    "status usuarios",
    "status de usuarios",
    "usuarios cadastrados",
    "listar usuarios",
    "quantos usuarios",
    "quantos ids",
}
USER_LIST_LIMIT = 30
ANNOUNCEMENT_COMMANDS = {"aviso", "avisar", "broadcast", "novidade"}
ANNOUNCEMENT_HEADER = "📣 Novidades do Butler"
ANNOUNCEMENT_MAX_LENGTH = 3400


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


def _parse_announcement(text):
    """Interpreta comandos administrativos sem perder o texto original do aviso.

    Formatos aceitos:
      /aviso <mensagem>                         -> prévia para todos
      /aviso confirmar <mensagem>              -> envia para todos
      /aviso id 2 <mensagem>                    -> prévia para um usuário
      /aviso confirmar id 2 <mensagem>          -> envia para um usuário
    """
    raw = (text or "").strip()
    match = re.match(r"^/(aviso|avisar|broadcast|novidade)(?:\s+|$)(.*)$", raw, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    command = match.group(1).lower()
    if command not in ANNOUNCEMENT_COMMANDS:
        return None

    rest = (match.group(2) or "").strip()
    confirmed = False
    confirm_match = re.match(r"^confirmar(?:\s+|$)(.*)$", rest, re.IGNORECASE | re.DOTALL)
    if confirm_match:
        confirmed = True
        rest = (confirm_match.group(1) or "").strip()

    target_user_id = None
    target_match = re.match(r"^id\s+(\d+)(?:\s+|$)(.*)$", rest, re.IGNORECASE | re.DOTALL)
    if target_match:
        target_user_id = int(target_match.group(1))
        rest = (target_match.group(2) or "").strip()
    else:
        all_match = re.match(r"^todos(?:\s+|$)(.*)$", rest, re.IGNORECASE | re.DOTALL)
        if all_match:
            rest = (all_match.group(1) or "").strip()

    return {
        "confirmed": confirmed,
        "target_user_id": target_user_id,
        "message": rest,
    }


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


def _announcement_text(message):
    return f"{ANNOUNCEMENT_HEADER}\n\n{message.strip()}"


def _confirmation_command(request):
    message = request["message"].strip()
    target = request.get("target_user_id")
    if target is not None:
        return f"/aviso confirmar id {target} {message}"
    return f"/aviso confirmar {message}"


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


async def _announcement_targets(db, owner_chat_id, target_user_id=None):
    if target_user_id is not None:
        row = await db.prepare(
            "SELECT id,telegram_chat_id,preferred_name,first_name,username,is_owner "
            "FROM users WHERE id=? LIMIT 1"
        ).bind(target_user_id).first()
        if not row:
            return []
        target_chat_id = int(_row(row, "telegram_chat_id", 0) or 0)
        if target_chat_id == int(owner_chat_id) or int(_row(row, "is_owner", 0) or 0):
            return []
        return [row]

    return await _rows(
        db.prepare(
            "SELECT id,telegram_chat_id,preferred_name,first_name,username,is_owner "
            "FROM users WHERE telegram_chat_id<>? AND COALESCE(is_owner,0)=0 ORDER BY id ASC"
        ).bind(int(owner_chat_id))
    )


async def _handle_announcement(db, token, chat_id, request):
    message = (request.get("message") or "").strip()
    if not message:
        await send_message(
            token,
            chat_id,
            "📣 Avisos administrativos\n\n"
            "• /aviso <mensagem> — mostra a prévia para todos\n"
            "• /aviso confirmar <mensagem> — envia para todos\n"
            "• /aviso id 2 <mensagem> — prévia para o usuário #2\n"
            "• /aviso confirmar id 2 <mensagem> — envia para o usuário #2",
        )
        return True

    if len(message) > ANNOUNCEMENT_MAX_LENGTH:
        await send_message(
            token,
            chat_id,
            f"⚠️ Aviso muito longo. Limite administrativo: {ANNOUNCEMENT_MAX_LENGTH} caracteres.",
        )
        return True

    targets = await _announcement_targets(db, chat_id, request.get("target_user_id"))
    if not targets:
        if request.get("target_user_id") is not None:
            text = "⚠️ Não encontrei esse ID ou ele é o próprio proprietário."
        else:
            text = "👥 Não há outros usuários cadastrados para receber o aviso."
        await send_message(token, chat_id, text)
        return True

    outgoing = _announcement_text(message)

    if not request.get("confirmed"):
        if request.get("target_user_id") is not None:
            target = targets[0]
            audience = f"1 usuário: #{_row(target, 'id')} · {_display_name(target)}"
        else:
            audience = f"{len(targets)} usuário(s), excluindo você"
        await send_message(
            token,
            chat_id,
            "📣 Prévia do aviso\n"
            f"Destinatários: {audience}\n\n"
            f"{outgoing}\n\n"
            "Nada foi enviado ainda. Para confirmar, mande exatamente:\n"
            f"{_confirmation_command(request)}",
        )
        return True

    sent = 0
    failed_ids = []
    for target in targets:
        target_id = int(_row(target, "id", 0) or 0)
        target_chat_id = int(_row(target, "telegram_chat_id", 0) or 0)
        try:
            result = await send_message(token, target_chat_id, outgoing)
            if delivery_ok(result):
                sent += 1
            else:
                failed_ids.append(target_id)
        except Exception as exc:
            print(
                f"[admin-announcement] delivery-error user_id={target_id} "
                f"type={type(exc).__name__} message={str(exc)[:180]}"
            )
            failed_ids.append(target_id)

    report = [f"📣 Aviso concluído: {sent}/{len(targets)} entregue(s)."]
    if failed_ids:
        report.append("Falha nos IDs internos: " + ", ".join(f"#{uid}" for uid in failed_ids))
    await send_message(token, chat_id, "\n".join(report))
    return True


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    announcement = _parse_announcement(text)
    status_command = _is_user_status_command(text)
    if announcement is None and not status_command:
        return False

    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    chat_id = int(chat_id)

    # O gate usa a identidade autoritativa do proprietário, não um parâmetro
    # vindo da mensagem nem apenas a coluna mutável do banco.
    if not is_owner(chat_id):
        await send_message(token, chat_id, "🔒 Esse recurso é administrativo.")
        return True

    if announcement is not None:
        return await _handle_announcement(db, token, chat_id, announcement)

    await send_message(
        token,
        chat_id,
        await _user_status_text(db),
        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
    )
    return True
