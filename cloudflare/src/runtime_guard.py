import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

from owner_profile import is_owner
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
GENERIC_WORKOUT_KB = [["📅 Treino de hoje", "📝 Registrar série"],["✅ Finalizar treino", "😕 Não consegui treinar hoje"],["📈 Progresso", "🔄 Reiniciar treinos"],["📥 Importar treino por PDF/texto"],["🏠 Menu principal"]]
TASK_KB = [["✅ Concluir tarefa", "⏰ Adiar tarefa"],["📌 Manter pendente", "🚫 Cancelar tarefa"],["⬅️ Voltar ao cotidiano"]]
ROUTINE_KB = [["➕ Adicionar rotina", "📋 Minhas rotinas"],["✅ Marcar rotina feita", "🗑️ Remover rotina"],["⬅️ Voltar ao cotidiano"]]
CANCEL_KB = [["❌ Cancelar ação"]]


def _kb(rows): return {"keyboard": rows, "resize_keyboard": True}
def _norm(text):
    v=unicodedata.normalize("NFKD",(text or "").lower());v="".join(c for c in v if not unicodedata.combining(c));return re.sub(r"[^a-z0-9 ]+"," ",v).strip()
def _row(row,key,default=None):
    if row is None:return default
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default
async def _rows(stmt):
    r=await stmt.all();data=getattr(r,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []
def _now():return datetime.now(timezone.utc).astimezone(LOCAL_TZ)
async def _send(token,chat,text,keyboard):return await send_message(token,chat,text,reply_markup=_kb(keyboard))
async def _uid(db,chat):
    r=await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat).first();return int(_row(r,"id")) if r else None
async def _set_state(db,uid,state,payload=""):
    import json
    await db.prepare("INSERT INTO user_sessions(user_id,state,payload,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET state=excluded.state,payload=excluded.payload,updated_at=CURRENT_TIMESTAMP").bind(uid,state,json.dumps(payload if isinstance(payload,dict) else {"value":payload},ensure_ascii=False)).run()
async def _state(db,uid):
    import json
    r=await db.prepare("SELECT state,payload FROM user_sessions WHERE user_id=?").bind(uid).first()
    try:p=json.loads(_row(r,"payload") or "{}")
    except Exception:p={}
    return _row(r,"state"),p
async def _clear(db,uid):await _set_state(db,uid,None,{})

async def ensure_runtime_schema(db):
    # Mantida apenas para compatibilidade/manual migration; não roda no caminho quente.
    return

async def _task_list(db,uid):
    rs=await _rows(db.prepare("SELECT id,title,due_date,due_time,status,postpone_count FROM daily_items WHERE user_id=? AND kind='tarefa' ORDER BY CASE status WHEN 'pendente' THEN 0 ELSE 1 END,due_date,id DESC LIMIT 25").bind(uid))
    if not rs:return "✅ Nenhuma tarefa cadastrada."
    out=["✅ Tarefas"]
    for r in rs:
        icon={"pendente":"⏳","concluido":"✅","cancelado":"🚫"}.get(_row(r,"status"),"•");when=""
        if _row(r,"due_date"):when=f" — {_row(r,'due_date')[8:10]}/{_row(r,'due_date')[5:7]}"+(f" {_row(r,'due_time')}" if _row(r,"due_time") else "")
        out.append(f"{icon} #{_row(r,'id')} {_row(r,'title')}{when}")
    out.append("\nUse os botões abaixo ou diga algo como `concluir #3` / `adiar #3 para amanhã às 18h`.")
    return "\n".join(out)

async def _find_task(db,uid,text):
    m=re.search(r"#?(\d+)",text or "")
    if m:
        r=await db.prepare("SELECT * FROM daily_items WHERE id=? AND user_id=? AND kind='tarefa'").bind(int(m.group(1)),uid).first()
        if r:return r
    target=re.sub(r"^(?:certo|ok|feito|concluir|conclui|finalizar|finaliza|cancelar|cancela|adiar|adia|manter|pendente)\s+","",text or "",flags=re.I).strip()
    if not target:return None
    rs=await _rows(db.prepare("SELECT * FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente'").bind(uid));matches=[r for r in rs if _norm(target) in _norm(_row(r,"title")) or _norm(_row(r,"title")) in _norm(target)]
    return matches[0] if len(matches)==1 else None

async def _routine_list(db,uid):
    rs=await _rows(db.prepare("SELECT id,name,category,time_hhmm,weekdays FROM routines WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    if not rs:return "🧘 Nenhuma rotina cadastrada. Use ➕ Adicionar rotina."
    return "🧘 Suas rotinas:\n"+"\n".join(f"• #{_row(r,'id')} {_row(r,'name')}"+(f" — {_row(r,'time_hhmm')}" if _row(r,'time_hhmm') else "")+(f" — {_row(r,'weekdays')}" if _row(r,'weekdays') else "")+f" [{_row(r,'category')}]" for r in rs)

async def _handle_state(db,token,chat,uid,text):
    state,payload=await _state(db,uid)
    if not state or not state.startswith("guard_"):return False
    if text in ("❌ Cancelar ação","/cancelar"):
        await _clear(db,uid);await _send(token,chat,"Cancelado.",TASK_KB if "task" in state else ROUTINE_KB);return True
    if state.startswith("guard_task_"):
        task=await _find_task(db,uid,text)
        if not task:
            await _send(token,chat,"Qual tarefa? Mande o número, por exemplo `#3`, ou o nome exato.",CANCEL_KB);return True
        tid=int(_row(task,"id"));title=_row(task,"title")
        if state=="guard_task_done":
            await db.prepare("UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?").bind(tid,uid).run();await _clear(db,uid);await _send(token,chat,f"✅ {title} concluída. Certo. Era só isso que eu precisava saber. 😌",TASK_KB);return True
        if state=="guard_task_pending":
            await db.prepare("UPDATE daily_items SET status='pendente',completed_at=NULL,cancelled_at=NULL WHERE id=? AND user_id=?").bind(tid,uid).run();await _clear(db,uid);await _send(token,chat,f"📌 {title} continua pendente. Não sumiu; só ganhou mais tempo para te encarar.",TASK_KB);return True
        if state=="guard_task_cancel":
            await db.prepare("UPDATE daily_items SET status='cancelado',cancelled_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?").bind(tid,uid).run();await _clear(db,uid);await _send(token,chat,f"🚫 {title} cancelada.",TASK_KB);return True
        if state=="guard_task_postpone":
            await _set_state(db,uid,"guard_task_postpone_when",{"id":tid,"title":title});await _send(token,chat,"Para quando? Ex.: `amanhã às 18h`, `daqui a 2 dias às 10h` ou `16/08 às 14h`.",CANCEL_KB);return True
    if state=="guard_task_postpone_when":
        from nlu import parse_date,parse_time,validate_future
        d=parse_date(text,_now().date());tm=parse_time(text)
        if not d:
            await _send(token,chat,"Não entendi a nova data. Ex.: `amanhã às 18h`.",CANCEL_KB);return True
        ok,msg=validate_future(d,tm,_now().replace(tzinfo=None))
        if not ok:await _send(token,chat,msg,CANCEL_KB);return True
        await db.prepare("UPDATE daily_items SET due_date=?,due_time=?,status='pendente',postpone_count=postpone_count+1,snoozed_until=? WHERE id=? AND user_id=?").bind(d.isoformat(),tm,(f"{d.isoformat()} {tm}" if tm else d.isoformat()),payload["id"],uid).run();await _clear(db,uid);await _send(token,chat,f"⏰ {payload['title']} adiada para {d.strftime('%d/%m')}"+(f" às {tm}" if tm else "")+". O calendário aceitou. Eu estou processando. 😏",TASK_KB);return True
    if state=="guard_routine_name":
        if not text:return True
        await _set_state(db,uid,"guard_routine_category",{"name":text});await _send(token,chat,"Essa rotina conta para qual meta? Inglês, Programação, Água, Alimentação, Musculação ou `Outra`.",CANCEL_KB);return True
    if state=="guard_routine_category":
        payload["category"]=text;await _set_state(db,uid,"guard_routine_when",payload);await _send(token,chat,"Quando? Ex.: `07:30 todos os dias`, `20:00 segunda, quarta, sexta` ou `sem horário`.",CANCEL_KB);return True
    if state=="guard_routine_when":
        n=_norm(text);tm=None;weekdays="todos os dias"
        m=re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b",text)
        if m:tm=f"{int(m.group(1)):02d}:{m.group(2)}"
        elif n not in ("sem horario","sem hora"):
            m=re.search(r"\b([01]?\d|2[0-3])h(?:([0-5]\d))?\b",n)
            if m:tm=f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}"
        days=[d for d in ("segunda","terça","quarta","quinta","sexta","sábado","domingo") if _norm(d) in n]
        if days:weekdays=",".join(days)
        await db.prepare("INSERT INTO routines(user_id,name,category,time_hhmm,weekdays,active) VALUES(?,?,?,?,?,1)").bind(uid,payload["name"],payload["category"],tm,weekdays).run();await _clear(db,uid);await _send(token,chat,f"🧘 Rotina `{payload['name']}` criada"+(f" às {tm}" if tm else "")+f". Meta ligada: {payload['category']}.",ROUTINE_KB);return True
    if state in ("guard_routine_done","guard_routine_remove"):
        m=re.search(r"#?(\d+)",text);r=None
        if m:r=await db.prepare("SELECT id,name,category FROM routines WHERE id=? AND user_id=? AND active=1").bind(int(m.group(1)),uid).first()
        if not r:
            rs=await _rows(db.prepare("SELECT id,name,category FROM routines WHERE user_id=? AND active=1").bind(uid));matches=[x for x in rs if _norm(text) in _norm(_row(x,"name")) or _norm(_row(x,"name")) in _norm(text)];r=matches[0] if len(matches)==1 else None
        if not r:await _send(token,chat,"Qual rotina? Use o #ID mostrado em Minhas rotinas.",CANCEL_KB);return True
        if state=="guard_routine_remove":
            await db.prepare("UPDATE routines SET active=0 WHERE id=? AND user_id=?").bind(_row(r,"id"),uid).run();msg=f"🗑️ {_row(r,'name')} removida."
        else:
            today=_now().date().isoformat();await db.prepare("INSERT INTO routine_logs(routine_id,log_date,status) VALUES(?,?,'feito') ON CONFLICT(routine_id,log_date) DO UPDATE SET status='feito'").bind(_row(r,"id"),today).run()
            g=await db.prepare("SELECT id FROM goals WHERE user_id=? AND lower(name)=lower(?) LIMIT 1").bind(uid,_row(r,"category")).first()
            if g:await db.prepare("INSERT INTO goal_progress(goal_id,amount,log_date,note) SELECT ?,1,?,? WHERE NOT EXISTS(SELECT 1 FROM goal_progress WHERE goal_id=? AND log_date=? AND note=?)").bind(_row(g,"id"),today,f"rotina:{_row(r,'id')}",_row(g,"id"),today,f"rotina:{_row(r,'id')}").run()
            msg=f"✅ {_row(r,'name')} feita hoje. E sim, contei isso na meta `{_row(r,'category')}` quando ela existe. 🔥"
        await _clear(db,uid);await _send(token,chat,msg,ROUTINE_KB);return True
    return False

async def handle_pre_dispatch(db, token: str, message: dict) -> bool:
    chat=message.get("chat") or {};chat_id=chat.get("id");text=(message.get("text") or "").strip()
    if chat_id is None:return False
    chat_id=int(chat_id);uid=await _uid(db,chat_id)
    if uid and await _handle_state(db,token,chat_id,uid,text):return True

    # O perfil genérico não recebe o protocolo pessoal do proprietário.
    if not is_owner(chat_id):
        if text=="🏋️ Musculação":await _send(token,chat_id,"🏋️ Musculação\n\nSeu treino começa vazio. Importe uma ficha por PDF/texto e depois acompanhe por aqui.",GENERIC_WORKOUT_KB);return True
        if text=="🚀 Começar os trabalhos":await _send(token,chat_id,"Esse botão pertence ao protocolo pessoal do proprietário. No seu perfil, basta importar sua ficha e usar Treino de hoje.",GENERIC_WORKOUT_KB);return True

    if not uid:return False
    if text=="✅ Tarefas":await _send(token,chat_id,await _task_list(db,uid),TASK_KB);return True
    if text=="🧘 Rotinas":await _send(token,chat_id,await _routine_list(db,uid),ROUTINE_KB);return True
    if text=="📋 Minhas rotinas":await _send(token,chat_id,await _routine_list(db,uid),ROUTINE_KB);return True
    if text=="➕ Adicionar rotina":await _set_state(db,uid,"guard_routine_name",{});await _send(token,chat_id,"Nome da rotina? Ex.: `Estudar inglês`.",CANCEL_KB);return True
    if text=="✅ Marcar rotina feita":await _set_state(db,uid,"guard_routine_done",{});await _send(token,chat_id,await _routine_list(db,uid)+"\n\nQual foi feita? Mande #ID ou nome.",CANCEL_KB);return True
    if text=="🗑️ Remover rotina":await _set_state(db,uid,"guard_routine_remove",{});await _send(token,chat_id,await _routine_list(db,uid)+"\n\nQual remover?",CANCEL_KB);return True
    if text=="✅ Concluir tarefa":await _set_state(db,uid,"guard_task_done",{});await _send(token,chat_id,await _task_list(db,uid)+"\n\nQual tarefa foi feita?",CANCEL_KB);return True
    if text=="📌 Manter pendente":await _set_state(db,uid,"guard_task_pending",{});await _send(token,chat_id,await _task_list(db,uid)+"\n\nQual continua pendente?",CANCEL_KB);return True
    if text=="🚫 Cancelar tarefa":await _set_state(db,uid,"guard_task_cancel",{});await _send(token,chat_id,await _task_list(db,uid)+"\n\nQual cancelar?",CANCEL_KB);return True
    if text=="⏰ Adiar tarefa":await _set_state(db,uid,"guard_task_postpone",{});await _send(token,chat_id,await _task_list(db,uid)+"\n\nQual tarefa quer adiar?",CANCEL_KB);return True

    # Respostas curtas: se só há uma tarefa pendente recente, `certo`, `ok`, `feito` concluem.
    if _norm(text) in ("certo","ok","feito","pronto","concluido","concluida"):
        rs=await _rows(db.prepare("SELECT id,title FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente' ORDER BY COALESCE(due_date,'9999-12-31'),COALESCE(due_time,'99:99'),id LIMIT 2").bind(uid))
        if len(rs)==1:
            r=rs[0];await db.prepare("UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP WHERE id=?").bind(_row(r,"id")).run();await _send(token,chat_id,f"✅ {_row(r,'title')} concluída. Certo. Era só isso. 😌",TASK_KB);return True
        if len(rs)>1:
            await _send(token,chat_id,"Tenho mais de uma tarefa pendente. Qual delas? Use `concluir #ID` ou o botão Concluir tarefa. Não vou sair dando baixa na sua vida no chute.",TASK_KB);return True

    # Ações naturais por ID/nome.
    n=_norm(text)
    if re.match(r"^(concluir|conclui|finalizar|finaliza|feito)\b",n):await _set_state(db,uid,"guard_task_done",{});return await _handle_state(db,token,chat_id,uid,text)
    if re.match(r"^(cancelar|cancela)\b",n):await _set_state(db,uid,"guard_task_cancel",{});return await _handle_state(db,token,chat_id,uid,text)
    if re.match(r"^(adiar|adia)\b",n):
        # Se já veio `para ...`, guarda a tarefa e pergunta só a nova data para evitar parser ambíguo.
        before=re.split(r"\s+para\s+",text,maxsplit=1,flags=re.I)[0];task=await _find_task(db,uid,before)
        if task:
            after=re.split(r"\s+para\s+",text,maxsplit=1,flags=re.I)
            await _set_state(db,uid,"guard_task_postpone_when",{"id":int(_row(task,"id")),"title":_row(task,"title")})
            if len(after)>1:return await _handle_state(db,token,chat_id,uid,after[1])
        await _set_state(db,uid,"guard_task_postpone",{});return await _handle_state(db,token,chat_id,uid,text)
    return False
