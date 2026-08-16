"""Gateway mínimo para escritas disparadas por camadas auxiliares.

Centraliza validação/idempotência. Library, memória e sugestões devem chamar estas
funções após confirmação em vez de reproduzir INSERTs próprios.
"""
import re

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
