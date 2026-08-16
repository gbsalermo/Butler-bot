import json
import re
import unicodedata

import companion_nlu_v2 as v2
from telegram_api import send_message

RELATIONS = {
    "mae": ("mãe", "mae"), "pai": ("pai",), "avo": ("avó", "avo", "avô"), "irma": ("irmã", "irma", "irmão", "irmao"),
    "tia": ("tia",), "tio": ("tio",), "prima": ("prima",), "primo": ("primo",),
    "amigo": ("amigo", "amiga"), "namorada": ("namorada", "namorado"), "colega": ("colega",), "ficante": ("ficante",),
    "esposa": ("esposa",), "marido": ("marido",),
}
RELATION_DISPLAY = {"mae":"mãe","pai":"pai","avo":"avó/avô","irma":"irmã/irmão","tia":"tia","tio":"tio","prima":"prima","primo":"primo","amigo":"amigo/amiga","namorada":"namorada/namorado","colega":"colega","ficante":"ficante","esposa":"esposa","marido":"marido"}
VEHICLES = ("carro", "moto", "bicicleta", "bike")
OBJECTS = ("notebook", "computador", "pc", "celular", "telefone", "tablet", "camera", "câmera", "violao", "violão", "guitarra")
BAD_NAMES = {"deve","vai","tem","esta","está","fica","ficar","com","sem","que","ele","ela","meu","minha","um","uma","pode","precisa"}


def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    value=re.sub(r"[^a-z0-9 ]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()


def _row(row,key,default=None):
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default


async def _rows(stmt):
    result=await stmt.all(); data=getattr(result,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []


async def _entities(db,uid):
    rs=await _rows(db.prepare("SELECT detail FROM natural_events WHERE user_id=? AND event_type='personal_entity' ORDER BY id DESC LIMIT 120").bind(uid))
    out=[]; seen=set()
    for r in rs:
        try:data=json.loads(_row(r,"detail") or "{}")
        except Exception:continue
        key=(_norm(data.get("name")),data.get("kind"))
        if data.get("name") and key not in seen: seen.add(key); out.append(data)
    return out


async def _save(db,uid,entity):
    rs=await _rows(db.prepare("SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='personal_entity' ORDER BY id DESC LIMIT 120").bind(uid))
    key=_norm(entity.get("name"))
    for r in rs:
        try:data=json.loads(_row(r,"detail") or "{}")
        except Exception:continue
        if _norm(data.get("name"))==key and data.get("kind")==entity.get("kind"):
            data.update({k:v for k,v in entity.items() if v not in (None,"")})
            await db.prepare("UPDATE natural_events SET detail=? WHERE id=?").bind(json.dumps(data,ensure_ascii=False),_row(r,"id")).run(); return
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'personal_entity',?)").bind(uid,json.dumps(entity,ensure_ascii=False)).run()


async def _delete(db,uid,name):
    rs=await _rows(db.prepare("SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='personal_entity' ORDER BY id DESC LIMIT 120").bind(uid)); removed=False
    target=_norm(name)
    for r in rs:
        try:data=json.loads(_row(r,"detail") or "{}")
        except Exception:continue
        if _norm(data.get("name"))==target:
            await db.prepare("DELETE FROM natural_events WHERE id=? AND user_id=?").bind(_row(r,"id"),uid).run(); removed=True
    return removed


def _valid_name(name): return bool(name and _norm(name) not in BAD_NAMES and len(_norm(name))>=2)


def _person_decl(text):
    for rel,words in RELATIONS.items():
        joined="|".join(re.escape(w) for w in words)
        patterns=[
            rf"(?:meu|minha)\s+(?:{joined})\s+(?:se chama|chama|e|é)\s+([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{{2,30}})",
            rf"tenho\s+(?:um|uma)\s+(?:{joined})\s+(?:chamad[oa]\s+)?([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{{2,30}})",
            rf"([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{{2,30}})\s+(?:e|é)\s+(?:meu|minha)\s+(?:{joined})",
        ]
        for p in patterns:
            m=re.search(p,text or "",flags=re.I)
            if m and _valid_name(m.group(1)): return {"kind":"person","name":m.group(1).capitalize(),"relation":rel}
    return None


def _vehicle_decl(text):
    m=re.search(r"meu\s+(carro|moto|bicicleta|bike)\s+(?:e|é)\s+(?:um|uma)?\s*([A-Za-z0-9ÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç .-]{2,60}?)(?:\s+de\s+(\d{4})|$)",text,flags=re.I)
    if not m:return None
    model=m.group(2).strip(" .,-")
    if not model:return None
    entity={"kind":"vehicle","name":m.group(1).lower(),"vehicle_type":m.group(1).lower(),"model":model}
    if m.group(3):entity["year"]=m.group(3)
    return entity


def _object_decl(text):
    for obj in OBJECTS:
        m=re.search(rf"meu\s+{re.escape(obj)}\s+(?:e|é)\s+(?:um|uma)?\s*([^,.!?]{{2,70}})",text or "",flags=re.I)
        if m:return {"kind":"object","name":obj,"description":m.group(1).strip()}
    return None


def _find(entities,text):
    n=_norm(text)
    for e in entities:
        name=_norm(e.get("name"))
        if name and re.search(r"\b"+re.escape(name)+r"\b",n):return e
    return None


def _describe(e):
    if e.get("kind")=="person": return f"{e.get('name')} é {RELATION_DISPLAY.get(e.get('relation'),e.get('relation'))} seu/sua."
    if e.get("kind")=="vehicle":
        year=f" {e.get('year')}" if e.get("year") else ""; return f"Seu {e.get('vehicle_type')} é {e.get('model')}{year}."
    if e.get("kind")=="object": return f"Seu {e.get('name')} é {e.get('description')}."
    return None


async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=_norm(text); entities=await _entities(db,uid)

    rm=re.search(r"(?:esquece|esqueça|apaga|apague|remove|remova)\s+(?:o\s+|a\s+)?([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,40})",text,flags=re.I)
    if rm and await _delete(db,uid,rm.group(1)):
        await send_message(token,int(chat_id),f"Fechado. Tirei {rm.group(1)} da memória."); return True

    declared=_person_decl(text) or _vehicle_decl(text) or _object_decl(text)
    if declared:
        await _save(db,uid,declared); desc=_describe(declared)
        await send_message(token,int(chat_id),f"Anotado. {desc} Vou guardar isso pra não te fazer repetir depois."); return True

    for rel,words in RELATIONS.items():
        if any(_norm(w) in n for w in words) and any(x in n for x in ("qual o nome","qual nome","quem e","quem é","lembra")):
            matches=[e for e in entities if e.get("kind")=="person" and e.get("relation")==rel]
            if matches:
                names=", ".join(e.get("name") for e in matches); await send_message(token,int(chat_id),f"Tenho aqui: {names}."); return True

    if any(v in n for v in VEHICLES) and any(x in n for x in ("qual","que","lembra","o que sabe")):
        matches=[e for e in entities if e.get("kind")=="vehicle" and (e.get("vehicle_type") in n or len([x for x in entities if x.get('kind')=='vehicle'])==1)]
        if matches: await send_message(token,int(chat_id),_describe(matches[0])); return True

    ref=_find(entities,text)
    if ref and any(x in n for x in ("quem e","quem é","o que voce sabe","o que você sabe","lembra","quem eh")):
        desc=_describe(ref)
        if desc: await send_message(token,int(chat_id),f"Lembro. {desc}"); return True

    return False
