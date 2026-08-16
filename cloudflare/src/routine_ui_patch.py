"""Ajustes de UX do menu de Rotinas.

Mantém edição acessível por botão, unifica os menus e instala a proteção de
entrega dos schedulers.
"""
import alert_diagnostics
import routine_integration
import runtime_guard
import scheduled_delivery_guard
from telegram_api import send_message

ROUTINE_KB=[
    ["➕ Adicionar rotina","✏️ Editar rotina"],
    ["📋 Minhas rotinas","✅ Marcar rotina feita"],
    ["🏁 Encerrar rotina hoje","🗑️ Remover rotina"],
    ["⬅️ Voltar ao cotidiano"],
]


def _kb(rows):return {"keyboard":rows,"resize_keyboard":True}


def install():
    # Unifica todos os pontos conhecidos que exibem o menu de Rotinas.
    runtime_guard.ROUTINE_KB=ROUTINE_KB
    routine_integration.ROUTINE_KB=ROUTINE_KB
    try:
        import academic_intelligence
        academic_intelligence.ROUTINE_KB=ROUTINE_KB
    except Exception:
        pass
    try:
        import app
        if hasattr(app,"ROUTINE_KB"):
            app.ROUTINE_KB=ROUTINE_KB
    except Exception:
        pass

    # Alertas agendados só entram no notification_log após confirmação real do Telegram.
    scheduled_delivery_guard.install()


async def handle_message(db,token,message):
    # Diagnóstico unificado para rotina, tarefa, compromisso, lembrete e aula.
    if await alert_diagnostics.handle_message(db,token,message):
        return True

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
