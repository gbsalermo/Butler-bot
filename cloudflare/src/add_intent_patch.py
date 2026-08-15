import json

import runtime_guard
from nlu import interpret
from telegram_api import send_message

CANCEL_KB = [["❌ Cancelar ação"]]

def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}

async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    if not row:
        return None
    try:
        return int(getattr(row, "id"))
    except Exception:
        return int(row["id"])

async def _set_state(db, uid, state, payload=None):
    await db.prepare(
        "INSERT INTO user_sessions(user_id,state,payload,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP) "
        "ON CONFLICT(user_id) DO UPDATE SET state=excluded.state,payload=excluded.payload,updated_at=CURRENT_TIMESTAMP"
    ).bind(uid, state, json.dumps(payload or {}, ensure_ascii=False)).run()

async def _send(token, chat_id, text):
    await send_message(token, chat_id, text, reply_markup=_kb(CANCEL_KB))

def install_add_intent_patch():
    original = runtime_guard.handle_pre_dispatch

    async def wrapped(db, token, message):
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        text = (message.get("text") or "").strip()
        if chat_id is not None and text:
            uid = await _uid(db, int(chat_id))
            if uid:
                parsed = interpret(text)
                if parsed and parsed[0] == "open_add":
                    kind = (parsed[1] or {}).get("kind")
                    if kind == "tarefa":
                        await _set_state(db, uid, "task_title", {})
                        await _send(token, int(chat_id), "Qual tarefa? Pode escrever só o que precisa fazer.")
                        return True
                    if kind == "compromisso":
                        await _set_state(db, uid, "appointment_title", {})
                        await _send(token, int(chat_id), "Qual compromisso?")
                        return True
                    if kind == "mercado":
                        await _set_state(db, uid, "grocery_add", {})
                        await _send(token, int(chat_id), "O que está faltando? Pode mandar `sal, açúcar, café`.")
                        return True
                    if kind == "rotina":
                        await _set_state(db, uid, "guard_routine_name", {})
                        await _send(token, int(chat_id), "Qual rotina? Ex.: `Estudar inglês`, `Beber água` ou `Programar 1h`.")
                        return True
        return await original(db, token, message)

    runtime_guard.handle_pre_dispatch = wrapped
