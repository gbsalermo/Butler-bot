from datetime import date

import app
import goal_operational as goals
import runtime_guard
from telegram_api import send_message

EDIT_KB = [["✏️ Nome", "📅 Prazo"], ["🎯 Valor-alvo", "🔓 Desvincular rotina"], ["⬅️ Voltar às metas"]]
CANCEL_KB = [["❌ Cancelar ação"]]


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _profile_list(db, uid):
    rows = await goals._rows(db.prepare("""
        SELECT g.id,g.name,p.goal_type,p.start_date,p.target_date,
               p.start_value,p.current_value,p.target_value,p.unit,p.status,
               r.name routine_name
        FROM goals g
        JOIN goal_profiles p ON p.goal_id=g.id
        LEFT JOIN routines r ON r.id=p.linked_routine_id
        WHERE g.user_id=? AND g.active=1 AND p.status!='removed'
        ORDER BY CASE p.status WHEN 'active' THEN 0 ELSE 1 END,g.id
    """).bind(uid))
    if not rows:
        return "🎯 Nenhuma meta criada ainda. Rotina sem objetivo é só burocracia com horário."
    out=["🎯 Suas metas"]
    today=app.now_local().date()
    for i,r in enumerate(rows,1):
        typ=goals._row(r,"goal_type"); status=goals._row(r,"status"); icon="✅" if status=="completed" else "🎯"
        line=f"{icon} {i}. {goals._row(r,'name')}"
        if typ=="habit":
            total=max(1,(date.fromisoformat(goals._row(r,"target_date"))-date.fromisoformat(goals._row(r,"start_date"))).days+1) if goals._row(r,"target_date") else 0
            count=await db.prepare("SELECT COUNT(DISTINCT log_date) n FROM goal_progress WHERE goal_id=?").bind(goals._row(r,"id")).first()
            done=int(goals._row(count,"n",0) or 0)
            line+=f" — {done}/{total or '?'} dia(s)"
            if goals._row(r,"routine_name"):line+=f" • 🧘 {goals._row(r,'routine_name')}"
        elif typ=="numeric":
            cur=goals._row(r,"current_value"); target=goals._row(r,"target_value"); unit=goals._row(r,"unit") or ""
            if cur is not None and target is not None:line+=f" — {float(cur):g} → {float(target):g} {unit}".rstrip()
        elif typ=="project":
            line+=f" — {float(goals._row(r,'current_value',0) or 0):.0f}%"
        if goals._row(r,"target_date"):
            d=date.fromisoformat(goals._row(r,"target_date"));line+=f" • até {d.strftime('%d/%m')}"
            if status=="active" and d<today:line+=" ⚠️"
        out.append(line)
    return "\n".join(out)


def install():
    # Substitui a listagem antiga: metas legadas usadas internamente continuam no
    # banco, mas não poluem a interface nova.
    goals._goal_list = _profile_list


async def _uid(db, chat_id):
    return await goals._uid(db,chat_id)


async def handle_message(db,token,message):
    text=(message.get("text") or "").strip();n=goals._norm(text)
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    chat_id=int(chat_id);uid=await _uid(db,chat_id)
    if uid is None:return False
    await goals.ensure_schema(db)
    state,payload=await runtime_guard._state(db,uid)

    if state and state.startswith("goal_edit_"):
        if text in ("❌ Cancelar ação","/cancelar","⬅️ Voltar às metas"):
            await runtime_guard._clear(db,uid);await send_message(token,chat_id,await _profile_list(db,uid),reply_markup=_kb(goals.GOAL_KB));return True
        if state=="goal_edit_select":
            goal,available=await goals._find_goal(db,uid,text)
            if not goal:
                await send_message(token,chat_id,"Escolha pelo número ou nome:\n"+"\n".join(f"{i}. {goals._row(g,'name')}" for i,g in enumerate(available,1)),reply_markup=_kb(CANCEL_KB));return True
            await runtime_guard._set_state(db,uid,"goal_edit_field",{"goal_id":int(goals._row(goal,"id")),"name":goals._row(goal,"name"),"type":goals._row(goal,"goal_type")})
            await send_message(token,chat_id,f"✏️ Editando {goals._row(goal,'name')}. O que quer mudar?",reply_markup=_kb(EDIT_KB));return True
        if state=="goal_edit_field":
            mapping={"✏️ Nome":"name","nome":"name","📅 Prazo":"deadline","prazo":"deadline","🎯 Valor-alvo":"target","valor alvo":"target","alvo":"target","🔓 Desvincular rotina":"unlink","desvincular rotina":"unlink"}
            field=mapping.get(text) or mapping.get(n)
            if not field:
                await send_message(token,chat_id,"Escolha Nome, Prazo, Valor-alvo ou Desvincular rotina.",reply_markup=_kb(EDIT_KB));return True
            if field=="unlink":
                await db.prepare("UPDATE goal_profiles SET linked_routine_id=NULL WHERE goal_id=?").bind(payload["goal_id"]).run();await runtime_guard._clear(db,uid)
                await send_message(token,chat_id,"🔓 Rotina desvinculada. A meta continua ativa, mas o progresso deixa de entrar automaticamente.",reply_markup=_kb(goals.GOAL_KB));return True
            if field=="target" and payload.get("type")!="numeric":
                await send_message(token,chat_id,"Valor-alvo numérico é usado nas metas Numéricas. Para hábito, mude o prazo; para projeto, use Registrar progresso.",reply_markup=_kb(EDIT_KB));return True
            await runtime_guard._set_state(db,uid,"goal_edit_value",{**payload,"field":field})
            prompt={"name":"Qual o novo nome?","deadline":"Qual o novo prazo? Use `DD/MM` ou `sem prazo`.","target":"Qual o novo valor-alvo?"}[field]
            await send_message(token,chat_id,prompt,reply_markup=_kb(CANCEL_KB));return True
        if state=="goal_edit_value":
            field=payload["field"];gid=payload["goal_id"]
            if field=="name":
                if not text:await send_message(token,chat_id,"O nome não pode ficar vazio.",reply_markup=_kb(CANCEL_KB));return True
                await db.prepare("UPDATE goals SET name=? WHERE id=? AND user_id=?").bind(text[:120],gid,uid).run();msg=f"✏️ Meta renomeada para {text[:120]}."
            elif field=="deadline":
                if n in ("sem prazo","sem data"):
                    value=None
                else:
                    d=app.parse_date(text,app.now_local().date())
                    if not d:await send_message(token,chat_id,"Não reconheci a data. Use `DD/MM`, `amanhã` ou `sem prazo`.",reply_markup=_kb(CANCEL_KB));return True
                    value=d.isoformat()
                await db.prepare("UPDATE goal_profiles SET target_date=? WHERE goal_id=?").bind(value,gid).run();msg="📅 Prazo atualizado"+(f" para {date.fromisoformat(value).strftime('%d/%m')}." if value else ": agora sem prazo.")
            else:
                value=goals._number(text)
                if value is None:await send_message(token,chat_id,"Manda um valor numérico, ex.: `80`.",reply_markup=_kb(CANCEL_KB));return True
                await db.prepare("UPDATE goal_profiles SET target_value=? WHERE goal_id=?").bind(value,gid).run();await db.prepare("UPDATE goals SET target_value=? WHERE id=?").bind(value,gid).run();msg=f"🎯 Novo valor-alvo: {value:g}."
            await runtime_guard._clear(db,uid);await send_message(token,chat_id,msg,reply_markup=_kb(goals.GOAL_KB));return True

    if text=="✏️ Editar meta" or n in ("editar meta","edita meta","alterar meta"):
        available=await goals._active_goals(db,uid)
        if not available:
            await send_message(token,chat_id,"Não há meta ativa para editar.",reply_markup=_kb(goals.GOAL_KB));return True
        await runtime_guard._set_state(db,uid,"goal_edit_select",{})
        await send_message(token,chat_id,"Qual meta quer editar?\n"+"\n".join(f"{i}. {goals._row(g,'name')}" for i,g in enumerate(available,1)),reply_markup=_kb(CANCEL_KB));return True
    return False
