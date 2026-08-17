import re
from datetime import date

import app
import goal_operational as goals
import runtime_guard
from telegram_api import send_message

CANCEL_KB=[["❌ Cancelar ação"]]


def _kb(rows):return {"keyboard":rows,"resize_keyboard":True}


async def handle_message(db,token,message):
    text=(message.get("text") or "").strip();n=goals._norm(text)
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    uid=await goals._uid(db,int(chat_id))
    if uid is None:return False
    await goals.ensure_schema(db)
    state,payload=await runtime_guard._state(db,uid)

    if state=="goal_relative_weight_start":
        if text in ("❌ Cancelar ação","/cancelar"):
            await runtime_guard._clear(db,uid);return False
        current=goals._number(text)
        if current is None:
            await send_message(token,int(chat_id),"Qual seu peso atual? Ex.: `90 kg`.",reply_markup=_kb(CANCEL_KB));return True
        delta=float(payload["delta"]);target=current-delta;today=app.now_local().date()
        data={"name":payload["name"],"type":"numeric","category":"numérica","start_date":today.isoformat(),"start_value":current,"current_value":current,"target_value":target,"unit":"kg"}
        await goals._create_goal(db,uid,data);await runtime_guard._clear(db,uid)
        await send_message(token,int(chat_id),f"🎯 Meta criada: {payload['name']}. Peso inicial {current:g} kg; alvo {target:g} kg. Agora cada atualização de peso mexe no progresso de verdade.",reply_markup=_kb(goals.GOAL_KB));return True

    if state=="goal_natural_project_deadline":
        if text in ("❌ Cancelar ação","/cancelar"):
            await runtime_guard._clear(db,uid);return False
        if n in ("sem prazo","sem data"):
            target=None
        else:
            d=app.parse_date(text,app.now_local().date())
            if not d:
                await send_message(token,int(chat_id),"Manda uma data como `30/09` ou `sem prazo`.",reply_markup=_kb(CANCEL_KB));return True
            target=d.isoformat()
        today=app.now_local().date();data={"name":payload["name"],"type":"project","category":"projeto","start_date":today.isoformat(),"target_date":target,"start_value":0,"current_value":0,"target_value":100,"unit":"%"}
        await goals._create_goal(db,uid,data);await runtime_guard._clear(db,uid)
        await send_message(token,int(chat_id),f"🏁 Meta de projeto criada: {payload['name']}"+(f" — até {date.fromisoformat(target).strftime('%d/%m')}" if target else " — sem prazo")+". Progresso começa em 0%.",reply_markup=_kb(goals.GOAL_KB));return True

    # Quero/meta perder 10 kg -> pergunta apenas o peso atual e calcula o alvo.
    m=re.search(r"(?:quero|meta(?: de)?|objetivo(?: de)?)\s+(?:é\s+|e\s+)?perder\s+(\d+(?:[.,]\d+)?)\s*kg\b",n)
    if m:
        delta=float(m.group(1).replace(",","."));name=f"Perder {delta:g} kg"
        await runtime_guard._set_state(db,uid,"goal_relative_weight_start",{"delta":delta,"name":name})
        await send_message(token,int(chat_id),f"🎯 {name}. Qual seu peso atual? Com isso eu calculo o alvo em vez de fingir que sei de onde estamos partindo.",reply_markup=_kb(CANCEL_KB));return True

    # Quero terminar/fazer o projeto X -> pergunta prazo, sem criar coisa vaga demais.
    m=re.search(r"(?:quero|meta(?: de)?|objetivo(?: de)?)\s+(?:é\s+|e\s+)?(?:terminar|finalizar|concluir|fazer)\s+(?:o\s+)?projeto\s+(.+)$",n)
    if m:
        name="Projeto "+m.group(1).strip().title()
        await runtime_guard._set_state(db,uid,"goal_natural_project_deadline",{"name":name})
        await send_message(token,int(chat_id),f"🏁 {name}. Tem prazo? Manda `DD/MM` ou `sem prazo`.",reply_markup=_kb(CANCEL_KB));return True
    return False
