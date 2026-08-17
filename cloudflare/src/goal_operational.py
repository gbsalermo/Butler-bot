import re
import unicodedata
from datetime import date, timedelta

import app
import routine_integration
import runtime_guard
from telegram_api import send_message

GOAL_KB = [
    ["➕ Nova meta", "📋 Minhas metas"],
    ["✅ Registrar progresso", "🔗 Vincular rotina"],
    ["✏️ Editar meta", "🏁 Concluir meta"],
    ["🗑️ Remover meta", "⬅️ Voltar ao cotidiano"],
]
TYPE_KB = [["🔥 Hábito", "📈 Numérica", "🏁 Projeto"], ["❌ Cancelar ação"]]
CANCEL_KB = [["❌ Cancelar ação"]]


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9%., ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _row(row, key, default=None):
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


async def ensure_schema(db):
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS goal_profiles (
            goal_id INTEGER PRIMARY KEY,
            goal_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            target_date TEXT,
            start_value REAL,
            current_value REAL,
            target_value REAL,
            unit TEXT,
            linked_routine_id INTEGER,
            status TEXT NOT NULL DEFAULT 'active',
            notes TEXT,
            completed_at TEXT,
            FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE CASCADE,
            FOREIGN KEY(linked_routine_id) REFERENCES routines(id) ON DELETE SET NULL
        )
    """).run()
    await db.prepare("CREATE INDEX IF NOT EXISTS idx_goal_profiles_status ON goal_profiles(status)").run()
    await db.prepare("CREATE INDEX IF NOT EXISTS idx_goal_profiles_routine ON goal_profiles(linked_routine_id)").run()


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


def _duration_days(text):
    n = _norm(text)
    m = re.search(r"(\d+)\s*(dia|dias|semana|semanas|mes|meses)", n)
    if not m:
        return None
    qty = int(m.group(1)); unit = m.group(2)
    if unit.startswith("dia"): return qty
    if unit.startswith("semana"): return qty * 7
    return qty * 30


def _number(text):
    m = re.search(r"-?\d+(?:[.,]\d+)?", text or "")
    return float(m.group(0).replace(",", ".")) if m else None


async def _goal_list(db, uid):
    rows = await _rows(db.prepare("""
        SELECT g.id,g.name,g.category,p.goal_type,p.start_date,p.target_date,
               p.start_value,p.current_value,p.target_value,p.unit,p.status,
               r.name routine_name
        FROM goals g
        LEFT JOIN goal_profiles p ON p.goal_id=g.id
        LEFT JOIN routines r ON r.id=p.linked_routine_id
        WHERE g.user_id=? AND g.active=1 AND COALESCE(p.status,'active')!='removed'
        ORDER BY CASE COALESCE(p.status,'active') WHEN 'active' THEN 0 ELSE 1 END,g.id
    """).bind(uid))
    if not rows:
        return "🎯 Nenhuma meta ativa. Um raro momento em que sua ambição resolveu tirar folga."
    out = ["🎯 Suas metas"]
    today = date.today()
    for i, r in enumerate(rows, 1):
        typ = _row(r, "goal_type") or "legacy"
        status = _row(r, "status") or "active"
        icon = "✅" if status == "completed" else "🎯"
        line = f"{icon} {i}. {_row(r,'name')}"
        if typ == "habit":
            total = 0
            if _row(r, "start_date") and _row(r, "target_date"):
                total = max(1, (date.fromisoformat(_row(r,"target_date")) - date.fromisoformat(_row(r,"start_date"))).days + 1)
            count_row = await db.prepare("SELECT COUNT(DISTINCT log_date) n FROM goal_progress WHERE goal_id=?").bind(_row(r,"id")).first()
            done = int(_row(count_row,"n",0) or 0)
            line += f" — {done}/{total or '?'} dia(s)"
            if _row(r,"routine_name"): line += f" • rotina: {_row(r,'routine_name')}"
        elif typ == "numeric":
            cur = _row(r,"current_value"); target = _row(r,"target_value"); unit = _row(r,"unit") or ""
            if cur is not None and target is not None: line += f" — {cur:g} → {target:g} {unit}".rstrip()
        elif typ == "project":
            cur = float(_row(r,"current_value",0) or 0)
            line += f" — {cur:.0f}%"
        if _row(r,"target_date"):
            d = date.fromisoformat(_row(r,"target_date"))
            line += f" • até {d.strftime('%d/%m')}"
            if status == "active" and d < today: line += " ⚠️ prazo passou"
        out.append(line)
    return "\n".join(out)


async def _active_goals(db, uid):
    return await _rows(db.prepare("""
        SELECT g.id,g.name,p.goal_type,p.current_value,p.target_value,p.unit,p.linked_routine_id
        FROM goals g JOIN goal_profiles p ON p.goal_id=g.id
        WHERE g.user_id=? AND g.active=1 AND p.status='active'
        ORDER BY g.id
    """).bind(uid))


async def _find_goal(db, uid, text):
    goals = await _active_goals(db, uid)
    n = _norm(text)
    if n.isdigit():
        idx = int(n) - 1
        return goals[idx] if 0 <= idx < len(goals) else None, goals
    matches = [g for g in goals if n and (n in _norm(_row(g,"name")) or _norm(_row(g,"name")) in n)]
    return (matches[0] if len(matches)==1 else None), goals


async def _finish_if_reached(db, goal):
    typ = _row(goal,"goal_type")
    cur = _row(goal,"current_value")
    target = _row(goal,"target_value")
    reached = False
    if typ == "project" and cur is not None and float(cur) >= 100: reached = True
    elif typ == "numeric" and cur is not None and target is not None:
        # Direção é inferida pelo valor inicial: emagrecimento cai, economia/carga pode subir.
        profile = await db.prepare("SELECT start_value FROM goal_profiles WHERE goal_id=?").bind(_row(goal,"id")).first()
        start = _row(profile,"start_value")
        if start is not None:
            reached = float(cur) <= float(target) if float(target) < float(start) else float(cur) >= float(target)
    if reached:
        await db.prepare("UPDATE goal_profiles SET status='completed',completed_at=CURRENT_TIMESTAMP WHERE goal_id=?").bind(_row(goal,"id")).run()
    return reached


async def _create_goal(db, uid, payload):
    name = payload["name"]
    category = payload.get("category") or payload["type"]
    await db.prepare("INSERT INTO goals(user_id,name,category,target_value,target_unit,period,active) VALUES(?,?,?,?,?,?,1)").bind(
        uid, name, category, payload.get("target_value"), payload.get("unit"), payload.get("period")
    ).run()
    row = await db.prepare("SELECT id FROM goals WHERE user_id=? ORDER BY id DESC LIMIT 1").bind(uid).first()
    gid = int(_row(row,"id"))
    await db.prepare("""
        INSERT INTO goal_profiles(goal_id,goal_type,start_date,target_date,start_value,current_value,target_value,unit,status)
        VALUES(?,?,?,?,?,?,?,?, 'active')
    """).bind(gid,payload["type"],payload["start_date"],payload.get("target_date"),payload.get("start_value"),payload.get("current_value"),payload.get("target_value"),payload.get("unit")).run()
    return gid


async def _habit_natural(db, uid, text):
    n = _norm(text)
    if not any(x in n for x in ("meta", "quero", "objetivo")):
        return None
    if not any(x in n for x in ("todo dia", "todos os dias", "diariamente")):
        return None
    days = _duration_days(text)
    if not days:
        return None
    cleaned = re.sub(r"^(quero|meta de|minha meta e|meu objetivo e)\s+", "", n)
    cleaned = re.sub(r"\s+(todo dia|todos os dias|diariamente).*", "", cleaned).strip()
    if not cleaned:
        return None
    today = app.now_local().date()
    payload = {"name": cleaned.capitalize(), "type":"habit", "category":"hábito", "start_date":today.isoformat(), "target_date":(today+timedelta(days=days-1)).isoformat(), "period":f"{days} dias"}
    gid = await _create_goal(db,uid,payload)
    routines = await _rows(db.prepare("SELECT id,name FROM routines WHERE user_id=? AND active=1").bind(uid))
    tokens = [t for t in _norm(cleaned).split() if len(t)>=4]
    matches = [r for r in routines if any(t in _norm(_row(r,"name")) for t in tokens)]
    if len(matches)==1:
        await db.prepare("UPDATE goal_profiles SET linked_routine_id=? WHERE goal_id=?").bind(_row(matches[0],"id"),gid).run()
        return f"🎯 Meta criada: {cleaned.capitalize()} por {days} dias. Vinculei com a rotina {_row(matches[0],'name')}; cumprir a rotina vai alimentar a meta automaticamente."
    return f"🎯 Meta criada: {cleaned.capitalize()} por {days} dias. Você pode usar 🔗 Vincular rotina para automatizar o progresso."


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None: return False
    chat_id = int(chat_id)
    uid = await _uid(db,chat_id)
    if uid is None: return False
    await ensure_schema(db)
    n = _norm(text)

    # Criação natural conservadora: apenas hábito com duração explícita.
    natural = await _habit_natural(db,uid,text)
    if natural:
        await send_message(token,chat_id,natural,reply_markup=_kb(GOAL_KB)); return True

    state,payload = await runtime_guard._state(db,uid)
    if state and state.startswith("goal_"):
        if text in ("❌ Cancelar ação","/cancelar"):
            await runtime_guard._clear(db,uid); await send_message(token,chat_id,"Meta cancelada. Ambição arquivada antes de virar burocracia.",reply_markup=_kb(GOAL_KB)); return True
        if state == "goal_type":
            types = {"🔥 Hábito":"habit","📈 Numérica":"numeric","🏁 Projeto":"project","habito":"habit","hábito":"habit","numerica":"numeric","numérica":"numeric","projeto":"project"}
            typ = types.get(text) or types.get(n)
            if not typ:
                await send_message(token,chat_id,"Escolha: Hábito, Numérica ou Projeto.",reply_markup=_kb(TYPE_KB)); return True
            payload["type"]=typ; await runtime_guard._set_state(db,uid,"goal_name",payload)
            await send_message(token,chat_id,"Qual é a meta? Ex.: `Estudar inglês`, `Chegar a 80 kg` ou `Finalizar projeto Butler`.",reply_markup=_kb(CANCEL_KB)); return True
        if state == "goal_name":
            payload["name"]=text; payload["start_date"]=app.now_local().date().isoformat()
            typ=payload["type"]
            if typ=="habit":
                await runtime_guard._set_state(db,uid,"goal_duration",payload); await send_message(token,chat_id,"Por quanto tempo? Ex.: `30 dias`, `1 mês` ou `8 semanas`.",reply_markup=_kb(CANCEL_KB)); return True
            if typ=="numeric":
                await runtime_guard._set_state(db,uid,"goal_numeric_start",payload); await send_message(token,chat_id,"Qual o valor atual? Ex.: `90 kg`, `R$ 0`, `5 km`.",reply_markup=_kb(CANCEL_KB)); return True
            await runtime_guard._set_state(db,uid,"goal_project_deadline",payload); await send_message(token,chat_id,"Tem prazo? Manda `DD/MM` ou `sem prazo`.",reply_markup=_kb(CANCEL_KB)); return True
        if state == "goal_duration":
            days=_duration_days(text)
            if not days:
                await send_message(token,chat_id,"Manda algo como `30 dias`, `1 mês` ou `8 semanas`.",reply_markup=_kb(CANCEL_KB)); return True
            start=date.fromisoformat(payload["start_date"]); payload["target_date"]=(start+timedelta(days=days-1)).isoformat(); payload["period"]=f"{days} dias"; payload["category"]="hábito"
            gid=await _create_goal(db,uid,payload); await runtime_guard._clear(db,uid)
            routines=await _rows(db.prepare("SELECT id,name FROM routines WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
            msg=f"🎯 Meta criada: {payload['name']} por {days} dias."
            if routines: msg += "\nUse 🔗 Vincular rotina para o progresso entrar automaticamente quando você cumprir a rotina."
            await send_message(token,chat_id,msg,reply_markup=_kb(GOAL_KB)); return True
        if state == "goal_numeric_start":
            v=_number(text)
            if v is None:
                await send_message(token,chat_id,"Preciso do valor atual, ex.: `90` ou `90 kg`.",reply_markup=_kb(CANCEL_KB)); return True
            payload["start_value"]=v; payload["current_value"]=v
            unit=re.sub(r".*?-?\d+(?:[.,]\d+)?\s*", "", text).strip(); payload["unit"]=unit
            await runtime_guard._set_state(db,uid,"goal_numeric_target",payload); await send_message(token,chat_id,"E qual é o valor-alvo? Ex.: `80 kg`.",reply_markup=_kb(CANCEL_KB)); return True
        if state == "goal_numeric_target":
            v=_number(text)
            if v is None:
                await send_message(token,chat_id,"Manda o valor-alvo, ex.: `80 kg`.",reply_markup=_kb(CANCEL_KB)); return True
            payload["target_value"]=v; payload["category"]="numérica"
            if not payload.get("unit"): payload["unit"]=re.sub(r".*?-?\d+(?:[.,]\d+)?\s*", "", text).strip()
            await _create_goal(db,uid,payload); await runtime_guard._clear(db,uid)
            await send_message(token,chat_id,f"🎯 Meta criada: {payload['name']} — {payload['start_value']:g} → {v:g} {payload.get('unit') or ''}. Agora eu preciso de progresso real, não de PowerPoint motivacional.",reply_markup=_kb(GOAL_KB)); return True
        if state == "goal_project_deadline":
            if n in ("sem prazo","sem data"):
                payload["target_date"]=None
            else:
                d=app.parse_date(text,app.now_local().date())
                if not d:
                    await send_message(token,chat_id,"Use `DD/MM`, `amanhã`, etc., ou `sem prazo`.",reply_markup=_kb(CANCEL_KB)); return True
                payload["target_date"]=d.isoformat()
            payload.update({"category":"projeto","start_value":0,"current_value":0,"target_value":100,"unit":"%"})
            await _create_goal(db,uid,payload); await runtime_guard._clear(db,uid)
            await send_message(token,chat_id,f"🏁 Projeto-meta criado: {payload['name']}. Progresso começa em 0%"+(f" e prazo {date.fromisoformat(payload['target_date']).strftime('%d/%m')}" if payload.get('target_date') else "")+".",reply_markup=_kb(GOAL_KB)); return True
        if state == "goal_progress_select":
            goal,goals=await _find_goal(db,uid,text)
            if not goal:
                await send_message(token,chat_id,"Escolha pelo número ou nome:\n"+"\n".join(f"{i}. {_row(g,'name')}" for i,g in enumerate(goals,1)),reply_markup=_kb(CANCEL_KB)); return True
            payload={"goal_id":int(_row(goal,"id")),"goal_type":_row(goal,"goal_type"),"name":_row(goal,"name")}
            await runtime_guard._set_state(db,uid,"goal_progress_value",payload)
            prompt="Quanto está agora?" if _row(goal,"goal_type")=="numeric" else ("Qual percentual concluído? Ex.: `40%`." if _row(goal,"goal_type")=="project" else "Meta de hábito avança pela rotina vinculada. Se fez hoje sem rotina, responda `feito`.")
            await send_message(token,chat_id,prompt,reply_markup=_kb(CANCEL_KB)); return True
        if state == "goal_progress_value":
            gid=payload["goal_id"]; typ=payload["goal_type"]; today=app.now_local().date().isoformat()
            if typ=="habit":
                if n not in ("feito","certo","ok","concluido","concluida"):
                    await send_message(token,chat_id,"Responda `feito` para registrar o dia.",reply_markup=_kb(CANCEL_KB)); return True
                await db.prepare("INSERT INTO goal_progress(goal_id,amount,log_date,note) SELECT ?,1,?,'manual' WHERE NOT EXISTS(SELECT 1 FROM goal_progress WHERE goal_id=? AND log_date=?)").bind(gid,today,gid,today).run()
                msg="🔥 Dia contabilizado na meta."
            else:
                v=_number(text)
                if v is None:
                    await send_message(token,chat_id,"Manda um número. Ex.: `84,5` ou `40%`.",reply_markup=_kb(CANCEL_KB)); return True
                if typ=="project": v=max(0,min(100,v))
                await db.prepare("UPDATE goal_profiles SET current_value=? WHERE goal_id=?").bind(v,gid).run()
                await db.prepare("INSERT INTO goal_progress(goal_id,amount,log_date,note) VALUES(?,?,?,'valor atual')").bind(gid,v,today).run()
                goal=await db.prepare("SELECT g.id,g.name,p.goal_type,p.current_value,p.target_value FROM goals g JOIN goal_profiles p ON p.goal_id=g.id WHERE g.id=?").bind(gid).first()
                reached=await _finish_if_reached(db,goal)
                msg=f"📈 {payload['name']}: progresso atualizado para {v:g}"+(". Meta concluída. ✅" if reached else ".")
            await runtime_guard._clear(db,uid); await send_message(token,chat_id,msg,reply_markup=_kb(GOAL_KB)); return True
        if state == "goal_link_select":
            goal,goals=await _find_goal(db,uid,text)
            if not goal:
                await send_message(token,chat_id,"Qual meta de hábito?\n"+"\n".join(f"{i}. {_row(g,'name')}" for i,g in enumerate(goals,1) if _row(g,"goal_type")=="habit"),reply_markup=_kb(CANCEL_KB)); return True
            if _row(goal,"goal_type")!="habit":
                await send_message(token,chat_id,"Vínculo automático com rotina é para metas de hábito. Peso e projeto recebem progresso manual.",reply_markup=_kb(GOAL_KB)); await runtime_guard._clear(db,uid); return True
            routines=await _rows(db.prepare("SELECT id,name FROM routines WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
            await runtime_guard._set_state(db,uid,"goal_link_routine",{"goal_id":int(_row(goal,"id")),"goal_name":_row(goal,"name")})
            await send_message(token,chat_id,"Qual rotina?\n"+"\n".join(f"{i}. {_row(r,'name')}" for i,r in enumerate(routines,1)),reply_markup=_kb(CANCEL_KB)); return True
        if state == "goal_link_routine":
            routines=await _rows(db.prepare("SELECT id,name FROM routines WHERE user_id=? AND active=1 ORDER BY name").bind(uid)); routine=None
            if n.isdigit() and 1<=int(n)<=len(routines): routine=routines[int(n)-1]
            else:
                ms=[r for r in routines if n in _norm(_row(r,"name")) or _norm(_row(r,"name")) in n]
                if len(ms)==1:routine=ms[0]
            if not routine:
                await send_message(token,chat_id,"Escolha a rotina pelo número ou nome.",reply_markup=_kb(CANCEL_KB)); return True
            await db.prepare("UPDATE goal_profiles SET linked_routine_id=? WHERE goal_id=?").bind(_row(routine,"id"),payload["goal_id"]).run(); await runtime_guard._clear(db,uid)
            await send_message(token,chat_id,f"🔗 {payload['goal_name']} vinculada a {_row(routine,'name')}. Quando a rotina for concluída no dia, a meta recebe o crédito automaticamente.",reply_markup=_kb(GOAL_KB)); return True
        if state in ("goal_finish_select","goal_remove_select"):
            goal,goals=await _find_goal(db,uid,text)
            if not goal:
                await send_message(token,chat_id,"Escolha pelo número ou nome:\n"+"\n".join(f"{i}. {_row(g,'name')}" for i,g in enumerate(goals,1)),reply_markup=_kb(CANCEL_KB)); return True
            if state=="goal_finish_select":
                await db.prepare("UPDATE goal_profiles SET status='completed',completed_at=CURRENT_TIMESTAMP WHERE goal_id=?").bind(_row(goal,"id")).run(); msg=f"🏁 {_row(goal,'name')} concluída. Pode comemorar; eu registro a evidência para quando você disser que nunca termina nada."
            else:
                await db.prepare("UPDATE goals SET active=0 WHERE id=?").bind(_row(goal,"id")).run(); await db.prepare("UPDATE goal_profiles SET status='removed' WHERE goal_id=?").bind(_row(goal,"id")).run(); msg=f"🗑️ {_row(goal,'name')} removida das metas ativas. Histórico preservado."
            await runtime_guard._clear(db,uid); await send_message(token,chat_id,msg,reply_markup=_kb(GOAL_KB)); return True

    if text in ("🎯 Metas","⬅️ Voltar às metas"):
        await send_message(token,chat_id,await _goal_list(db,uid),reply_markup=_kb(GOAL_KB)); return True
    if text=="➕ Nova meta":
        await runtime_guard._set_state(db,uid,"goal_type",{}); await send_message(token,chat_id,"Que tipo de meta?\n🔥 Hábito — repetir algo por um período\n📈 Numérica — peso, dinheiro, distância etc.\n🏁 Projeto — acompanhar de 0 a 100%",reply_markup=_kb(TYPE_KB)); return True
    if text=="📋 Minhas metas":
        await send_message(token,chat_id,await _goal_list(db,uid),reply_markup=_kb(GOAL_KB)); return True
    if text=="✅ Registrar progresso":
        goals=await _active_goals(db,uid); await runtime_guard._set_state(db,uid,"goal_progress_select",{})
        await send_message(token,chat_id,"Qual meta?\n"+"\n".join(f"{i}. {_row(g,'name')}" for i,g in enumerate(goals,1)),reply_markup=_kb(CANCEL_KB)); return True
    if text=="🔗 Vincular rotina":
        goals=await _active_goals(db,uid); habits=[g for g in goals if _row(g,"goal_type")=="habit"]; await runtime_guard._set_state(db,uid,"goal_link_select",{})
        await send_message(token,chat_id,"Qual meta de hábito quer ligar a uma rotina?\n"+"\n".join(f"{i}. {_row(g,'name')}" for i,g in enumerate(habits,1)),reply_markup=_kb(CANCEL_KB)); return True
    if text=="✏️ Editar meta":
        await send_message(token,chat_id,"Por enquanto, edite registrando novo progresso ou remova/recrie a meta. Na próxima revisão eu separo edição de prazo, nome e alvo sem reabrir um wizard gigante.",reply_markup=_kb(GOAL_KB)); return True
    if text=="🏁 Concluir meta":
        goals=await _active_goals(db,uid); await runtime_guard._set_state(db,uid,"goal_finish_select",{})
        await send_message(token,chat_id,"Qual meta quer marcar como concluída?\n"+"\n".join(f"{i}. {_row(g,'name')}" for i,g in enumerate(goals,1)),reply_markup=_kb(CANCEL_KB)); return True
    if text=="🗑️ Remover meta":
        goals=await _active_goals(db,uid); await runtime_guard._set_state(db,uid,"goal_remove_select",{})
        await send_message(token,chat_id,"Qual meta quer retirar das ativas? O histórico fica salvo.\n"+"\n".join(f"{i}. {_row(g,'name')}" for i,g in enumerate(goals,1)),reply_markup=_kb(CANCEL_KB)); return True
    return False


def install():
    original_save = routine_integration._save_checkpoint

    async def save_with_goal_link(db, uid, routine, target_time=None):
        done, scheduled, complete = await original_save(db,uid,routine,target_time)
        if complete:
            await ensure_schema(db)
            profiles=await _rows(db.prepare("SELECT goal_id FROM goal_profiles WHERE linked_routine_id=? AND status='active'").bind(int(_row(routine,"id"))))
            today=app.now_local().date().isoformat()
            for p in profiles:
                gid=int(_row(p,"goal_id"))
                await db.prepare("INSERT INTO goal_progress(goal_id,amount,log_date,note) SELECT ?,1,?,'linked_routine' WHERE NOT EXISTS(SELECT 1 FROM goal_progress WHERE goal_id=? AND log_date=?)").bind(gid,today,gid,today).run()
                prof=await db.prepare("SELECT start_date,target_date FROM goal_profiles WHERE goal_id=?").bind(gid).first()
                if _row(prof,"target_date"):
                    total=max(1,(date.fromisoformat(_row(prof,"target_date"))-date.fromisoformat(_row(prof,"start_date"))).days+1)
                    count=await db.prepare("SELECT COUNT(DISTINCT log_date) n FROM goal_progress WHERE goal_id=?").bind(gid).first()
                    if int(_row(count,"n",0) or 0)>=total:
                        await db.prepare("UPDATE goal_profiles SET status='completed',completed_at=CURRENT_TIMESTAMP WHERE goal_id=?").bind(gid).run()
        return done,scheduled,complete

    routine_integration._save_checkpoint = save_with_goal_link
