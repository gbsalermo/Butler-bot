"""Memória pessoal complementar para preferências e fatos explícitos.

Só persiste construções declarativas claras. Não tenta inferir personalidade a partir
de conversa solta. Tudo é isolado por user_id.
"""
import json
import re

import companion_nlu_v2 as v2
from language_context import normalize_informal
from telegram_api import send_message

PATTERNS=(
    ("likes",r"(?:eu )?gosto de (?P<value>.+)"),
    ("dislikes",r"(?:eu )?nao gosto de (?P<value>.+)"),
    ("preference",r"(?:eu )?prefiro (?P<value>.+)"),
    ("football_team",r"(?:meu time|torco pro|torco para o|torço pro|torço para o) (?:e |é )?(?P<value>.+)"),
    ("city",r"(?:eu )?moro em (?P<value>.+)"),
)

async def _rows(stmt):
    res=await stmt.all(); data=getattr(res,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []

def _row(row,key,default=None):
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default

async def _save(db,uid,key,value):
    norm=normalize_informal(value)[:160]
    if not norm:return
    rows=await _rows(db.prepare("SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='personal_fact' ORDER BY id DESC LIMIT 100").bind(uid))
    for row in rows:
        try:data=json.loads(_row(row,"detail") or "{}")
        except Exception:continue
        if data.get("key")==key and normalize_informal(data.get("value") or "")==norm:return
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'personal_fact',?)").bind(uid,json.dumps({"key":key,"value":value.strip()[:160]},ensure_ascii=False)).run()

async def _facts(db,uid):
    rows=await _rows(db.prepare("SELECT detail FROM natural_events WHERE user_id=? AND event_type='personal_fact' ORDER BY id DESC LIMIT 100").bind(uid)); out=[]
    for row in rows:
        try:data=json.loads(_row(row,"detail") or "{}")
        except Exception:continue
        if data.get("key") and data.get("value"):out.append(data)
    return out

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=normalize_informal(text)

    if any(q in n for q in ("o que voce sabe sobre mim","oq voce sabe sobre mim","o que lembra de mim","oq lembra de mim")):
        facts=await _facts(db,uid)
        if not facts:return False
        labels={"likes":"Você gosta de","dislikes":"Você não gosta de","preference":"Você prefere","football_team":"Seu time é","city":"Você mora em"}
        lines=[]; seen=set()
        for fact in facts:
            sig=(fact["key"],normalize_informal(fact["value"]))
            if sig in seen:continue
            seen.add(sig); lines.append(f"• {labels.get(fact['key'],'Tenho registrado')}: {fact['value']}")
            if len(lines)>=8:break
        await send_message(token,int(chat_id),"Do que você me contou explicitamente, eu tenho isso:\n"+"\n".join(lines)+"\n\nNão completo as lacunas no chute.")
        return True

    for key,pattern in PATTERNS:
        m=re.fullmatch(pattern,n)
        if not m:continue
        value=m.group("value").strip(" .,!?")
        if len(value)<2 or len(value)>160:return False
        await _save(db,uid,key,value)
        # Declaração casual: guarda sem transformar a conversa num formulário.
        return False
    return False
