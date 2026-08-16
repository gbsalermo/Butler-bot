"""Escape operacional absoluto para /start.

Para usuários já cadastrados, /start limpa apenas estado temporário do chat e
volta ao menu principal. Dados permanentes nunca são tocados.
"""
import app
import runtime_guard
from telegram_api import send_message


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def handle_start_reset(db, token, message):
    text=(message.get("text") or "").strip().lower()
    if text not in ("/start", "/start@butlersal_bot"):
        return False
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    uid=await runtime_guard._uid(db,int(chat_id))
    if not uid:
        # Usuário novo segue para o onboarding normal do app.
        return False

    # user_sessions concentra os wizards do app/runtime_guard/routine editing.
    await db.prepare("DELETE FROM user_sessions WHERE user_id=?").bind(uid).run()

    # Contexto operacional curto pode ser descartado num reinício manual.
    try:
        await db.prepare("DELETE FROM conversation_context WHERE user_id=?").bind(uid).run()
    except Exception:
        pass

    # Referências conversacionais recentes também não devem sobreviver a um
    # reset explícito; memórias pessoais usam outras tabelas e permanecem intactas.
    try:
        await db.prepare("DELETE FROM natural_events WHERE user_id=? AND event_type='context'").bind(uid).run()
    except Exception:
        pass

    await send_message(
        token,
        int(chat_id),
        "🧹 Pronto. Zerei o estado temporário deste chat e voltei ao início. Seus dados continuam onde estavam.",
        reply_markup=_kb(app.MAIN_KB),
    )
    return True
