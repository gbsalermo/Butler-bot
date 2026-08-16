"""Memória pessoal complementar para preferências e fatos explícitos.

Só persiste construções declarativas claras. Não tenta inferir personalidade a partir
de conversa solta. Tudo é isolado por user_id.
"""
import json
import re

import companion_nlu_v2 as v2
from deterministic_memory import _entities
from language_context import normalize_informal
from telegram_api import send_message

PATTERNS=(
    ("likes",r"(?:eu )?gosto de (?P<value>.+)"),
    ("dislikes",r"(?:eu )?nao gosto de (?P<value>.+)"),
    ("preference",r"(?:eu )?prefiro (?P<value>.+)"),
    ("football_team",r"(?:meu time|torco pro|torco para o|torço pro|torço para o) (?:e |é )?(?P<value>.+)"),
    ("city",r"(?:eu )?moro em (?P<value>.+)"),
)
LABELS={"likes":"Você gosta de","dislikes":"Você não gosta de","preference":"Você prefere","football_team":"Seu time é","city":"Você mora em"}

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
    if not norm:return False
    rows=await _rows(db.prepare("SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='personal_fact' ORDER BY id DESC LIMIT 100").bind(uid))
    for row in rows:
        try:data=json.loads(_row(row,"detail") or "{}")
        except Exception:continue
        if data.get("key")==key and normalize_informal(data.get("value") or "")==norm:return False
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'personal_fact',?)").bind(uid,json.dumps({"key":key,"value":value.strip()[:160]},ensure_ascii=False)).run()
    return True

async def _delete_fact(db,uid,key,value):
    target=normalize_informal(value); removed=False
    rows=await _rows(db.prepare("SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='personal_fact' ORDER BY id DESC LIMIT 100").bind(uid))
    for row in rows:
        try:data=json.loads(_row(row,"detail") or "{}")
        except Exception:continue
        if data.get("key")==key and normalize_informal(data.get("value") or "")==target:
            await db.prepare("DELETE FROM natural_events WHERE id=? AND user_id=?").bind(_row(row,"id"),uid).run(); removed=True
    return removed

async def _facts(db,uid):
    rows=await _rows(db.prepare("SELECT detail FROM natural_events WHERE user_id=? AND event_type='personal_fact' ORDER BY id DESC LIMIT 100").bind(uid)); out=[]
    for row in rows:
        try:data=json.loads(_row(row,"detail") or "{}")
        except Exception:continue
        if data.get("key") and data.get("value"):out.append(data)
    return out

def _describe_entity(e):
    kind=e.get("kind"); name=e.get("name")
    if kind=="pet":
        extra=f", {e.get('color')}" if e.get("color") else ""
        return f"• {name}: seu {e.get('species') or 'pet'}{extra}"
    if kind=="person":return f"• {name}: relação {e.get('relation') or 'pessoal'}"
    if kind=="vehicle":
        year=f" {e.get('year')}" if e.get("year") else ""
        return f"• {e.get('vehicle_type') or name}: {e.get('model') or name}{year}"
    if kind=="object":return f"• {name}: {e.get('description') or 'objeto pessoal'}"
    return None

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=normalize_informal(text)

    # Mapa pessoal consultável: fatos + entidades estruturadas.
    if any(q in n for q in ("o que voce sabe sobre mim","o que lembra de mim","me fala o que sabe de mim","o que voce lembra de mim")):
        facts=await _facts(db,uid); entities=await _entities(db,uid); lines=[]; seen=set()
        for entity in entities:
            line=_describe_entity(entity)
            if line and line not in seen:seen.add(line); lines.append(line)
            if len(lines)>=8:break
        for fact in facts:
            sig=(fact["key"],normalize_informal(fact["value"]))
            if sig in seen:continue
            seen.add(sig); lines.append(f"• {LABELS.get(fact['key'],'Tenho registrado')}: {fact['value']}")
            if len(lines)>=12:break
        if not lines:
            await send_message(token,int(chat_id),"Ainda tenho pouca coisa sua registrada de forma explícita. Prefiro isso a inventar biografia."); return True
        await send_message(token,int(chat_id),"Do que você me contou e eu consegui estruturar, tenho isso:\n"+"\n".join(lines)+"\n\nO resto eu não completo no chute.")
        return True

    # Correções simples de preferência.
    forget=re.fullmatch(r"(?:esquece|apaga) que (?:eu )?(gosto de|nao gosto de|prefiro) (.+)",n)
    if forget:
        kind={"gosto de":"likes","nao gosto de":"dislikes","prefiro":"preference"}[forget.group(1)]
        value=forget.group(2).strip(); removed=await _delete_fact(db,uid,kind,value)
        await send_message(token,int(chat_id),("Fechado. Tirei isso da memória." if removed else "Não achei isso salvo na memória.")); return True

    for key,pattern in PATTERNS:
        m=re.fullmatch(pattern,n)
        if not m:continue
        value=m.group("value").strip(" .,!?")
        if len(value)<2 or len(value)>160:return False
        created=await _save(db,uid,key,value)
        if created:
            if key=="likes":msg=f"Justo. Vou guardar que você gosta de {value}."
            elif key=="dislikes":msg=f"Anotado. {value} não entra na lista de coisas que eu vou te empurrar depois."
            elif key=="preference":msg=f"Fechado. Vou considerar que você prefere {value}."
            elif key=="football_team":msg=f"Registrado. Seu time é {value}. Isso pode ou não virar material de provocação futura."
            else:msg=f"Anotado. Vou lembrar de {value} quando fizer sentido."
        else:msg="Isso já estava na minha memória. Pelo menos uma coisa aqui não precisou ser cadastrada duas vezes."
        await send_message(token,int(chat_id),msg); return True
    return False
