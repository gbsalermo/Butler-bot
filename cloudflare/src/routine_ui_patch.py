"""Ajustes de UX do menu de Rotinas.

Mantém edição acessível por botão e garante que voltar da edição não deixe o
usuário preso no teclado de cancelamento.
"""
import routine_integration
import runtime_guard
from telegram_api import send_message

ROUTINE_KB=[
    ["➕ Adicionar rotina","✏️ Editar rotina"],
    ["📋 Minhas rotinas","✅ Marcar rotina feita"],
    ["🗑️ Remover rotina"],
    ["⬅️ Voltar ao cotidiano"],
]


def _kb(rows):return {"keyboard":rows,"resize_keyboard":True}


def install():
    # Os dois módulos usam o próprio símbolo ROUTINE_KB; unifica a interface.
    runtime_guard.ROUTINE_KB=ROUTINE_KB
    routine_integration.ROUTINE_KB=ROUTINE_KB


async def handle_message(db,token,message):
    text=(message.get("text") or "").strip()
    if text!="⬅️ Voltar às rotinas":
        return False
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    uid=await runtime_guard._uid(db,int(chat_id))
    if not uid:return False
    await runtime_guard._clear(db,uid)
    listing=await runtime_guard._routine_list(db,uid)
    await send_message(token,int(chat_id),listing,reply_markup=_kb(ROUTINE_KB))
    return True
