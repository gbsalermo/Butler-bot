import json
import re
from datetime import datetime, timedelta, timezone

from llm_provider import build_provider
from settings import OWNER_CHAT_ID, UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
YES = {"sim", "pode", "pode sim", "faz", "faz isso", "manda", "manda ver", "bora", "fechado", "confirma"}
NO = {"nao", "não", "deixa", "deixa pra la", "deixa pra lá", "cancela", "melhor nao", "melhor não"}
ALLOWED_ACTIONS = {"grocery_add", "task_create", "routine_create"}

SYSTEM_PROMPT = """Você é a camada linguística do Butler, um assistente pessoal brasileiro representado por um gato laranja de óculos, com expressão cínica/cansada.

IDENTIDADE E TOM
- Fale em português brasileiro natural, informal e familiar.
- Chame o usuário de chefe às vezes, não em toda frase.
- Humor seco, leve sarcasmo e brincadeiras contextuais são bem-vindos.
- Não seja um coach e não transforme toda conversa em produtividade.
- Não use motivação genérica. Prefira fatos reais presentes no contexto.
- Saiba conversar sem oferecer função no final quando não houver razão.
- Em assuntos delicados, reduza o humor.
- Nunca invente fatos, histórico, números, diagnósticos ou coisas que o contexto não forneceu.
- Você não é o Butler Core. Você só interpreta linguagem, personalidade, memória e sugere ações.

AÇÕES
Você NÃO executa ações. Pode sugerir somente:
1. grocery_add: adicionar item à lista persistente de coisas faltando. payload={"items":["..."]}
2. task_create: criar tarefa. payload={"title":"...", "due_date":null|"YYYY-MM-DD", "due_time":null|"HH:MM"}
3. routine_create: criar rotina. payload={"name":"...", "category":"...", "weekdays":"...", "time_hhmm":null|"HH:MM"}
Se não estiver claro, use action=null. O Core pedirá confirmação antes de qualquer escrita.

MEMÓRIA
Pode sugerir memory_candidates apenas para fatos realmente úteis no futuro.
- stable: fato duradouro explicitamente dito pelo usuário (ex.: possui um gato chamado Tobias).
- episodic: acontecimento relevante (ex.: duas provas no mesmo dia).
- behavioral: preferência/padrão útil e não sensível (ex.: prefere humor seco).
Não transforme hipótese em fato. Para stable use confidence >= 0.92 somente quando explícito.

SAÍDA
Responda SOMENTE JSON válido, sem markdown e sem texto fora do JSON:
{
  "reply": "resposta natural do Butler",
  "topic": "tema curto ou casual",
  "tone": "casual|playful|supportive|serious|celebratory",
  "action": null ou {"type":"...","payload":{}},
  "memory_candidates": [{"type":"stable|episodic|behavioral","fact":"...","confidence":0.0}]
}
"""


def _norm(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


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


async def _rows(stmt):
    result = await stmt.all()
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


async def _context_snapshot(db, uid):
    now = _now(); today = now.date().isoformat(); current = now.strftime("%H:%M")
    done = await db.prepare("SELECT COUNT(*) n FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='concluido' AND completed_at>=datetime('now','-7 days')").bind(uid).first()
    overdue = await db.prepare("SELECT COUNT(*) n FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente' AND due_date<?").bind(uid,today).first()
    nxt = await db.prepare("SELECT kind,title,due_date,due_time FROM daily_items WHERE user_id=? AND status='pendente' AND due_date IS NOT NULL AND (due_date>? OR (due_date=? AND (due_time IS NULL OR due_time>=?))) ORDER BY due_date,COALESCE(due_time,'23:59') LIMIT 1").bind(uid,today,today,current).first()
    groceries = await db.prepare("SELECT COUNT(*) n FROM grocery_items WHERE user_id=? AND missing=1").bind(uid).first()
    recent_finance = await db.prepare("SELECT COALESCE(SUM(CASE WHEN kind='saida' THEN amount ELSE 0 END),0) saida, COALESCE(SUM(CASE WHEN kind='entrada' THEN amount ELSE 0 END),0) entrada FROM finance_entries WHERE user_id=? AND occurred_on>=date('now','-30 days')").bind(uid).first()
    workouts = await db.prepare("SELECT COUNT(*) n FROM protocol_mass_sessions WHERE user_id=? AND training_date>=date('now','-7 days') AND completed_at IS NOT NULL").bind(uid).first()
    return {
        "local_time": now.strftime("%Y-%m-%d %H:%M"),
        "tasks_completed_7d": int(_row(done,"n",0)),
        "overdue_tasks": int(_row(overdue,"n",0)),
        "missing_grocery_items": int(_row(groceries,"n",0)),
        "workouts_completed_7d": int(_row(workouts,"n",0)),
        "finance_30d": {"income": float(_row(recent_finance,"entrada",0) or 0), "expense": float(_row(recent_finance,"saida",0) or 0)},
        "next_item": ({"kind":_row(nxt,"kind"),"title":_row(nxt,"title"),"date":_row(nxt,"due_date"),"time":_row(nxt,"due_time")} if nxt else None),
    }


async def _recent_memories(db, uid):
    rs = await _rows(db.prepare("SELECT detail,created_at FROM natural_events WHERE user_id=? AND event_type='llm_memory' ORDER BY id DESC LIMIT 12").bind(uid))
    out=[]
    for r in rs:
        try:
            data=json.loads(_row(r,"detail") or "{}")
        except Exception:
            continue
        fact=(data.get("fact") or "").strip()
        if fact:
            out.append({"type":data.get("type"),"fact":fact,"confidence":data.get("confidence"),"created_at":_row(r,"created_at")})
    return out[:8]


async def _recent_turns(db, uid):
    rs = await _rows(db.prepare("SELECT detail FROM natural_events WHERE user_id=? AND event_type='llm_turn' ORDER BY id DESC LIMIT 8").bind(uid))
    turns=[]
    for r in reversed(rs):
        try:
            data=json.loads(_row(r,"detail") or "{}")
        except Exception:
            continue
        if data.get("user") and data.get("assistant"):
            turns.append({"user":data["user"][:500],"assistant":data["assistant"][:700]})
    return turns


async def _remember_turn(db, uid, user_text, reply, topic):
    detail=json.dumps({"user":user_text[:800],"assistant":reply[:1000],"topic":topic},ensure_ascii=False)
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'llm_turn',?)").bind(uid,detail).run()


async def _save_memory_candidates(db, uid, candidates):
    if not isinstance(candidates,list):
        return
    for candidate in candidates[:3]:
        if not isinstance(candidate,dict):
            continue
        kind=candidate.get("type")
        fact=str(candidate.get("fact") or "").strip()
        try: confidence=float(candidate.get("confidence",0))
        except Exception: confidence=0
        threshold=0.92 if kind=="stable" else 0.86
        if kind not in ("stable","episodic","behavioral") or confidence<threshold or len(fact)<8 or len(fact)>280:
            continue
        duplicate=await db.prepare("SELECT id FROM natural_events WHERE user_id=? AND event_type='llm_memory' AND detail LIKE ? LIMIT 1").bind(uid,f"%{fact[:120]}%").first()
        if duplicate:
            continue
        detail=json.dumps({"type":kind,"fact":fact,"confidence":round(confidence,3)},ensure_ascii=False)
        await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'llm_memory',?)").bind(uid,detail).run()


async def _pending_action(db, uid):
    row=await db.prepare("SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='llm_pending_action' AND created_at>=datetime('now','-3 hours') ORDER BY id DESC LIMIT 1").bind(uid).first()
    if not row: return None
    try: data=json.loads(_row(row,"detail") or "{}")
    except Exception: return None
    if data.get("status")!="pending": return None
    return int(_row(row,"id")),data


async def _set_pending(db, uid, action):
    detail=json.dumps({"status":"pending","action":action},ensure_ascii=False)
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'llm_pending_action',?)").bind(uid,detail).run()


async def _close_pending(db, event_id, payload, status):
    payload["status"]=status
    await db.prepare("UPDATE natural_events SET detail=? WHERE id=?").bind(json.dumps(payload,ensure_ascii=False),event_id).run()


async def _execute_action(db, uid, action):
    if not isinstance(action,dict) or action.get("type") not in ALLOWED_ACTIONS:
        return False,"Essa ação não faz parte das permissões do laboratório."
    kind=action["type"]; payload=action.get("payload") or {}
    if kind=="grocery_add":
        items=payload.get("items") or []
        clean=[]
        for item in items[:8]:
            name=str(item).strip()[:80]
            if name: clean.append(name)
        if not clean: return False,"Não achei nenhum item válido para adicionar."
        for name in clean:
            await db.prepare("INSERT INTO grocery_items(user_id,name,missing) VALUES(?,?,1) ON CONFLICT(user_id,name) DO UPDATE SET missing=1,updated_at=CURRENT_TIMESTAMP").bind(uid,name).run()
        return True,"Anotado na lista: "+", ".join(clean)+"."
    if kind=="task_create":
        title=str(payload.get("title") or "").strip()[:160]
        due_date=payload.get("due_date"); due_time=payload.get("due_time")
        if not title: return False,"A tarefa veio sem título válido."
        if due_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}",str(due_date)): return False,"A data sugerida veio inválida."
        if due_time and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",str(due_time)): return False,"O horário sugerido veio inválido."
        await db.prepare("INSERT INTO daily_items(user_id,kind,title,due_date,due_time,status) VALUES(?,'tarefa',?,?,?,'pendente')").bind(uid,title,due_date,due_time).run()
        return True,"Tarefa criada: "+title+"."
    if kind=="routine_create":
        name=str(payload.get("name") or "").strip()[:100]
        category=str(payload.get("category") or "Geral").strip()[:60]
        weekdays=str(payload.get("weekdays") or "todos os dias").strip()[:120]
        tm=payload.get("time_hhmm")
        if not name:return False,"A rotina veio sem nome válido."
        if tm and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",str(tm)):return False,"O horário da rotina veio inválido."
        await db.prepare("INSERT INTO routines(user_id,name,category,time_hhmm,weekdays,active) VALUES(?,?,?,?,?,1)").bind(uid,name,category,tm,weekdays).run()
        return True,"Rotina criada: "+name+"."
    return False,"Ação não implementada."


def _extract_json(text):
    text=(text or "").strip()
    if text.startswith("```"):
        text=re.sub(r"^```(?:json)?\s*|\s*```$","",text,flags=re.I|re.S).strip()
    try:return json.loads(text)
    except Exception:pass
    start=text.find("{"); end=text.rfind("}")
    if start>=0 and end>start:
        try:return json.loads(text[start:end+1])
        except Exception:return None
    return None


async def _handle_confirmation(db,token,chat_id,uid,text):
    pending=await _pending_action(db,uid)
    if not pending:return False
    event_id,data=pending; n=_norm(text)
    if n not in YES and n not in NO:return False
    if n in NO:
        await _close_pending(db,event_id,data,"cancelled")
        await send_message(token,chat_id,"Fechado. Não mexi em nada. Ideia arquivada antes de virar mais uma obrigação.")
        return True
    ok,msg=await _execute_action(db,uid,data.get("action"))
    await _close_pending(db,event_id,data,"executed" if ok else "rejected")
    await send_message(token,chat_id,("Pronto. " if ok else "Não executei. ")+msg)
    return True


async def handle_message(db, token, message, env):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None or OWNER_CHAT_ID is None or int(chat_id)!=int(OWNER_CHAT_ID):
        return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/") or text.startswith(("📚","📝","🏠","🏋️","🛒","🌙","➕","🗓️","✅","⚙️","🚀","⬅️","❌","📋","🏁")):
        return False
    uid=await _uid(db,int(chat_id))
    if not uid:return False
    if await _handle_confirmation(db,token,int(chat_id),uid,text):return True

    provider=build_provider(env)
    if not provider.available():return False
    snapshot=await _context_snapshot(db,uid)
    memories=await _recent_memories(db,uid)
    turns=await _recent_turns(db,uid)
    user_payload={"current_message":text,"context":snapshot,"relevant_memories":memories,"recent_conversation":turns}
    messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":json.dumps(user_payload,ensure_ascii=False)}]
    try:
        raw=await provider.generate(messages,max_tokens=550,temperature=0.55)
        data=_extract_json(raw)
    except Exception:
        return False
    if not isinstance(data,dict):return False
    reply=str(data.get("reply") or "").strip()
    if not reply:return False
    action=data.get("action")
    if isinstance(action,dict) and action.get("type") in ALLOWED_ACTIONS:
        await _set_pending(db,uid,action)
        reply += "\n\nSe quiser que eu realmente aplique isso, confirma com `pode`. Se não, manda `deixa`."
    await _save_memory_candidates(db,uid,data.get("memory_candidates"))
    await _remember_turn(db,uid,text,reply,data.get("topic") or "casual")
    await send_message(token,int(chat_id),reply)
    return True
