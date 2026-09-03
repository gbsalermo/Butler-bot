"""Gateway mínimo para escritas disparadas por camadas auxiliares.

Centraliza validação/idempotência. Library, memória, Inbox e sugestões devem chamar
estas funções após confirmação em vez de reproduzir INSERTs próprios.
"""
import re


def _row(row,key,default=None):
    if row is None:return default
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default


async def add_grocery_items(db,user_id,items):
    clean=[]
    for item in items or []:
        value=re.sub(r"\s+"," ",str(item or "").strip())[:80]
        if value and value.lower() not in {x.lower() for x in clean}:clean.append(value)
    if not clean:return []
    for item in clean:
        await db.prepare("INSERT INTO grocery_items(user_id,name,missing) VALUES(?,?,1) ON CONFLICT(user_id,name) DO UPDATE SET missing=1,updated_at=CURRENT_TIMESTAMP").bind(user_id,item).run()
    return clean

async def create_routine(db,user_id,name,time_hhmm=None,weekdays="todos os dias",category="Geral"):
    name=re.sub(r"\s+"," ",str(name or "").strip())[:100]
    if not name:return False,"nome vazio"
    if time_hhmm and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",str(time_hhmm)):return False,"horário inválido"
    exists=await db.prepare("SELECT id FROM routines WHERE user_id=? AND lower(name)=lower(?) AND active=1 LIMIT 1").bind(user_id,name).first()
    if exists:return True,"já existia"
    await db.prepare("INSERT INTO routines(user_id,name,category,time_hhmm,weekdays,active) VALUES(?,?,?,?,?,1)").bind(user_id,name,str(category or "Geral")[:60],time_hhmm,str(weekdays or "todos os dias")[:120]).run()
    return True,"criada"

async def create_task(db,user_id,title,due_date=None,due_time=None,details=None):
    title=re.sub(r"\s+"," ",str(title or "").strip())[:140]
    if not title:return False
    if due_time and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",str(due_time)):return False
    await db.prepare("INSERT INTO daily_items(user_id,kind,title,details,due_date,due_time,status) VALUES(?,'tarefa',?,?,?,?, 'pendente')").bind(user_id,title,details,due_date,due_time).run()
    return True


def _clean_daily_item(kind,title,due_date=None,due_time=None):
    if kind not in {"tarefa","compromisso"}:return None
    title=re.sub(r"\s+"," ",str(title or "").strip())[:140]
    if not title:return None
    if due_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}",str(due_date)):return None
    if due_time and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",str(due_time)):return None
    return title,due_date,due_time


async def create_daily_item_from_inbox(db,user_id,inbox_id,kind,title,due_date=None,due_time=None):
    """Cria tarefa/compromisso uma única vez para um item da Inbox.

    ``daily_items.source_inbox_id`` possui índice UNIQUE. Se o Telegram repetir a
    mesma atualização após uma falha parcial, a consulta devolve o alvo já criado
    em vez de duplicá-lo.
    """
    clean=_clean_daily_item(kind,title,due_date,due_time)
    if not clean:return None
    title,due_date,due_time=clean
    inbox_id=int(inbox_id);user_id=int(user_id)
    existing=await db.prepare(
        "SELECT id,user_id,kind FROM daily_items WHERE source_inbox_id=? LIMIT 1"
    ).bind(inbox_id).first()
    if existing:
        if int(_row(existing,"user_id"))!=user_id or _row(existing,"kind")!=kind:return None
        return int(_row(existing,"id"))
    await db.prepare(
        "INSERT OR IGNORE INTO daily_items(user_id,kind,title,due_date,due_time,status,source_inbox_id) "
        "VALUES(?,?,?,?,?,'pendente',?)"
    ).bind(user_id,kind,title,due_date,due_time,inbox_id).run()
    row=await db.prepare(
        "SELECT id,user_id,kind FROM daily_items WHERE source_inbox_id=? LIMIT 1"
    ).bind(inbox_id).first()
    if not row or int(_row(row,"user_id"))!=user_id or _row(row,"kind")!=kind:return None
    return int(_row(row,"id"))
