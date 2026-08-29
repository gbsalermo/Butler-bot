"""Fluxo seguro de prévia/confirmação de avisos administrativos.

O texto do aviso fica salvo temporariamente no D1. Os botões carregam apenas uma
chave curta no callback_data, evitando repetir a mensagem e respeitando o limite
do Telegram para callbacks.
"""

import re
import secrets

import admin_diagnostics
from owner_profile import is_owner
from telegram_api import answer_callback, delivery_ok, send_message

PENDING_TTL_HOURS = 2
CALLBACK_PREFIX = "admin_notice"


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


async def ensure_schema(db):
    await db.prepare(
        """
        CREATE TABLE IF NOT EXISTS admin_pending_announcements (
            pending_key TEXT PRIMARY KEY,
            owner_chat_id INTEGER NOT NULL,
            target_user_id INTEGER,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    ).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_admin_pending_owner_status "
        "ON admin_pending_announcements(owner_chat_id,status,created_at)"
    ).run()


def _callback_data(action, pending_key):
    return f"{CALLBACK_PREFIX}:{action}:{pending_key}"


def _parse_callback(data):
    match = re.fullmatch(rf"{CALLBACK_PREFIX}:(send|cancel):([a-f0-9]{{12}})", data or "")
    if not match:
        return None
    return {"action": match.group(1), "pending_key": match.group(2)}


def _confirmation_keyboard(pending_key):
    return {
        "inline_keyboard": [[
            {"text": "✅ Confirmar envio", "callback_data": _callback_data("send", pending_key)},
            {"text": "❌ Cancelar", "callback_data": _callback_data("cancel", pending_key)},
        ]]
    }


def _is_preview_request(request):
    return bool(request is not None and not request.get("confirmed"))


async def _save_pending(db, owner_chat_id, request):
    await ensure_schema(db)
    pending_key = secrets.token_hex(6)
    await db.prepare(
        "INSERT INTO admin_pending_announcements"
        "(pending_key,owner_chat_id,target_user_id,message,status) VALUES(?,?,?,?, 'pending')"
    ).bind(
        pending_key,
        int(owner_chat_id),
        request.get("target_user_id"),
        (request.get("message") or "").strip(),
    ).run()
    return pending_key


async def _load_pending(db, owner_chat_id, pending_key):
    await ensure_schema(db)
    return await db.prepare(
        "SELECT pending_key,owner_chat_id,target_user_id,message,status,created_at "
        "FROM admin_pending_announcements "
        "WHERE pending_key=? AND owner_chat_id=? "
        "AND status='pending' "
        f"AND datetime(created_at) >= datetime('now','-{PENDING_TTL_HOURS} hours') "
        "LIMIT 1"
    ).bind(pending_key, int(owner_chat_id)).first()


async def _mark_status(db, pending_key, old_status, new_status):
    await db.prepare(
        "UPDATE admin_pending_announcements SET status=?,updated_at=CURRENT_TIMESTAMP "
        "WHERE pending_key=? AND status=?"
    ).bind(new_status, pending_key, old_status).run()


async def _preview(db, token, chat_id, request):
    message = (request.get("message") or "").strip()
    if not message:
        await send_message(
            token,
            chat_id,
            "📣 Avisos administrativos\n\n"
            "• /aviso <mensagem> — prévia para todos\n"
            "• /aviso id 2 <mensagem> — prévia para o usuário #2\n\n"
            "Depois é só tocar em ✅ Confirmar envio ou ❌ Cancelar.",
        )
        return True

    if len(message) > admin_diagnostics.ANNOUNCEMENT_MAX_LENGTH:
        await send_message(
            token,
            chat_id,
            f"⚠️ Aviso muito longo. Limite administrativo: "
            f"{admin_diagnostics.ANNOUNCEMENT_MAX_LENGTH} caracteres.",
        )
        return True

    targets = await admin_diagnostics._announcement_targets(
        db, chat_id, request.get("target_user_id")
    )
    if not targets:
        text = (
            "⚠️ Não encontrei esse ID ou ele é o próprio proprietário."
            if request.get("target_user_id") is not None
            else "👥 Não há outros usuários cadastrados para receber o aviso."
        )
        await send_message(token, chat_id, text)
        return True

    pending_key = await _save_pending(db, chat_id, request)
    if request.get("target_user_id") is not None:
        target = targets[0]
        audience = (
            f"1 usuário: #{_row(target, 'id')} · "
            f"{admin_diagnostics._display_name(target)}"
        )
    else:
        audience = f"{len(targets)} usuário(s), excluindo você"

    await send_message(
        token,
        chat_id,
        "📣 Prévia do aviso\n"
        f"Destinatários: {audience}\n\n"
        f"{admin_diagnostics._announcement_text(message)}\n\n"
        "Nada foi enviado ainda.",
        reply_markup=_confirmation_keyboard(pending_key),
    )
    return True


async def _deliver_pending(db, token, chat_id, row):
    pending_key = _row(row, "pending_key")
    target_user_id = _row(row, "target_user_id")
    if target_user_id is not None:
        target_user_id = int(target_user_id)

    # Marca antes de enviar. Um segundo clique encontra o aviso fora de 'pending'
    # e não dispara uma segunda transmissão.
    await _mark_status(db, pending_key, "pending", "sending")

    targets = await admin_diagnostics._announcement_targets(db, chat_id, target_user_id)
    if not targets:
        await _mark_status(db, pending_key, "sending", "sent")
        await send_message(token, chat_id, "👥 Não há destinatários válidos para esse aviso.")
        return

    outgoing = admin_diagnostics._announcement_text(_row(row, "message", ""))
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

    await _mark_status(db, pending_key, "sending", "sent")
    report = [f"📣 Aviso concluído: {sent}/{len(targets)} entregue(s)."]
    if failed_ids:
        report.append("Falha nos IDs internos: " + ", ".join(f"#{uid}" for uid in failed_ids))
    await send_message(token, chat_id, "\n".join(report))


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    request = admin_diagnostics._parse_announcement(text)
    if not _is_preview_request(request):
        # Confirmação digitada continua funcionando pelo handler legado.
        return False

    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    chat_id = int(chat_id)

    if not is_owner(chat_id):
        await send_message(token, chat_id, "🔒 Esse recurso é administrativo.")
        return True

    return await _preview(db, token, chat_id, request)


async def handle_callback(db, token, callback):
    parsed = _parse_callback(callback.get("data") or "")
    if parsed is None:
        return False

    message = callback.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    callback_id = callback.get("id")
    if chat_id is None:
        if callback_id:
            await answer_callback(token, callback_id, "Não consegui identificar o chat.")
        return True
    chat_id = int(chat_id)

    if not is_owner(chat_id):
        if callback_id:
            await answer_callback(token, callback_id, "Ação administrativa bloqueada.")
        return True

    row = await _load_pending(db, chat_id, parsed["pending_key"])
    if not row:
        if callback_id:
            await answer_callback(token, callback_id, "Aviso expirado ou já processado.")
        return True

    if parsed["action"] == "cancel":
        await _mark_status(db, parsed["pending_key"], "pending", "cancelled")
        if callback_id:
            await answer_callback(token, callback_id, "Aviso cancelado.")
        await send_message(token, chat_id, "❌ Aviso cancelado. Nada foi enviado.")
        return True

    if callback_id:
        await answer_callback(token, callback_id, "Enviando aviso…")
    await _deliver_pending(db, token, chat_id, row)
    return True
