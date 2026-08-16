"""Ajustes de UX do menu de Rotinas.

Mantém edição acessível por botão, unifica teclados e oferece diagnóstico textual
para investigar checkpoints sem poluir a interface principal.
"""
import json
from datetime import datetime, timedelta, timezone

import routine_integration
import runtime_guard
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ=timezone(timedelta(hours=UTC_OFFSET_HOURS))
ROUTINE_KB=[
    ["➕ Adicionar rotina","✏️ Editar rotina"],
    ["📋 Minhas rotinas","✅ Marcar rotina feita"],
    ["🏁 Encerrar rotina hoje","🗑️ Remover rotina"],
    ["⬅️ Voltar ao cotidiano"],
]


def _kb(rows):return {"keyboard":rows,"resize_keyboard":True}
def _row(row,key,default=None):
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default
async def _rows(stmt):
    result=await stmt.all();data=getattr(result,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []


def install():
    runtime_guard.ROUTINE_KB=ROUTINE_KB
    routine_integration.ROUTINE_KB=ROUTINE_KB
    try:
        import academic_intelligence
        academic_intelligence.ROUTINE_KB=ROUTINE_KB
    except Exception:pass
    try:
        import app
        if hasattr(app,"ROUTINE_KB"):app.ROUTINE_KB=ROUTINE_KB
    except Exception:pass

async def _diagnostic(db,uid):
    now=datetime.now(timezone.utc).astimezone(LOCAL_TZ);today=now.date()
    state=await db.prepare("SELECT COALESCE(day_off,0) day_off FROM assistant_state WHERE user_id=?").bind(uid).first()
    out=[f"🧪 Diagnóstico de rotinas — {now.strftime('%d/%m %H:%M')}",f"Day-off: {'sim' if int(_row(state,'day_off',0) or 0) else 'não'}"]
    routines=await _rows(db.prepare("SELECT id,name,time_hhmm,weekdays FROM routines WHERE user_id=? AND active=1 ORDER BY id").bind(uid))
    if not routines:return "\n".join(out+["Nenhuma rotina ativa."])
    for routine in routines:
        rid=int(_row(routine,"id"));times=routine_integration._times(_row(routine,"time_hhmm"))
        done=await routine_integration._status(db,rid,today,times)
        out.append(f"\n🧘 #{rid} {_row(routine,'name')}")
        out.append(f"Dias: {_row(routine,'weekdays') or 'todos os dias'}")
        if not routine_integration._applies(_row(routine,'weekdays'),today):
            out.append("Hoje: rotina não se aplica")
            continue
        if not times:
            out.append("Horários: sem horário")
            continue
        for t in times:
            key=f"routine:{rid}:{today.isoformat()}:{t}"
            notif=await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid,key).first()
            if t in done:status="✅ feito"
            elif notif:status="🔔 já notificado"
            else:status="⏳ pendente"
            out.append(f"• {t} — {status}")
    out.append("\nSe um horário vencido aparecer como ⏳ pendente, o scheduler ainda deveria enviá-lo. Se aparecer ✅ feito, o progresso diário está bloqueando o alerta; se aparecer 🔔 já notificado, o log diz que o envio já ocorreu.")
    return "\n".join(out)

async def handle_message(db,token,message):
    text=(message.get("text") or "").strip();norm=text.lower().replace("ó","o").replace("ô","o").replace("í","i")
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    uid=await runtime_guard._uid(db,int(chat_id))
    if not uid:return False
    if norm in {"diagnostico rotinas","diagnostico de rotinas","debug rotinas","status rotinas"}:
        await send_message(token,int(chat_id),await _diagnostic(db,uid),reply_markup=_kb(ROUTINE_KB));return True
    if text!="⬅️ Voltar às rotinas":return False
    await runtime_guard._clear(db,uid)
    listing=await runtime_guard._routine_list(db,uid)
    await send_message(token,int(chat_id),listing,reply_markup=_kb(ROUTINE_KB))
    return True
