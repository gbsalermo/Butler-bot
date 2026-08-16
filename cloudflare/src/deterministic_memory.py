import json
import re
import unicodedata

import academic_intelligence as ai
import companion_nlu_v2 as v2
from nlu import parse_date, parse_time
from settings import OWNER_CHAT_ID
from telegram_api import send_message

PET_SPECIES = ("gato", "gata", "cachorro", "cachorra", "cao", "cão")
PET_SUPPLIES = {"racao": "ração", "sache": "sachê", "areia": "areia", "petisco": "petisco"}
COLORS = ("laranja", "preto", "preta", "branco", "branca", "cinza", "marrom", "rajado", "rajada")
INVALID_NAMES = {
    "deve","vai","esta","está","ta","tá","tem","fica","ficar","ficou","anda","vive","precisa","preciso",
    "quer","pode","podem","ele","ela","que","sem","com","tambem","também","meio","muito","um","uma"
}


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _row(row, key, default=None):
    if row is None: return default
    try: return getattr(row, key)
    except Exception:
        try: return row[key]
        except Exception: return default


async def _rows(stmt):
    result = await stmt.all(); data = getattr(result, "results", None)
    if data is None: return []
    try: return list(data)
    except Exception: return data.to_py() if hasattr(data, "to_py") else []


async def _save_entity(db, uid, entity):
    name = str(entity.get("name") or "").strip()
    if not name: return
    existing = await _rows(db.prepare("SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='personal_entity' ORDER BY id DESC LIMIT 80").bind(uid))
    target = _norm(name)
    for row in existing:
        try: data = json.loads(_row(row, "detail") or "{}")
        except Exception: continue
        if _norm(data.get("name") or "") == target:
            merged = dict(data)
            for key, value in entity.items():
                if value not in (None, "", []): merged[key] = value
            await db.prepare("UPDATE natural_events SET detail=? WHERE id=?").bind(json.dumps(merged, ensure_ascii=False), _row(row, "id")).run(); return
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'personal_entity',?)").bind(uid, json.dumps(entity, ensure_ascii=False)).run()


async def _entities(db, uid):
    rows = await _rows(db.prepare("SELECT detail FROM natural_events WHERE user_id=? AND event_type='personal_entity' ORDER BY id DESC LIMIT 80").bind(uid))
    out=[]; seen=set()
    for row in rows:
        try: data=json.loads(_row(row,"detail") or "{}")
        except Exception: continue
        name=str(data.get("name") or "").strip(); key=_norm(name)
        if name and key not in seen: seen.add(key); out.append(data)
    return out


def _valid_name(name):
    n=_norm(name)
    return bool(n and n not in INVALID_NAMES and len(n)>=2)


def _pet_declaration(text):
    patterns = [
        r"(?:tenho|adotei|peguei)\s+(?:um|uma)\s+(gato|gata|cachorro|cachorra|cao|cão)\s+(?:chamad[oa]\s+)?([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})",
        r"meu\s+(gato|gata|cachorro|cachorra|cao|cão)\s+(?:chamad[oa]\s+)([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})",
        r"([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})\s+(?:e|é)\s+(?:o\s+|a\s+)?meu\s+(gato|gata|cachorro|cachorra|cao|cão)",
    ]
    for index, pattern in enumerate(patterns):
        m=re.search(pattern,text or "",flags=re.I)
        if not m: continue
        species,name=(m.group(1),m.group(2)) if index<2 else (m.group(2),m.group(1))
        if not _valid_name(name): continue
        return {"kind":"pet","name":name.capitalize(),"species":_norm(species)}
    return None


def _color(text):
    n=_norm(text)
    for color in COLORS:
        if _norm(color) in n:return _norm(color)
    return None


def _supply(text):
    n=_norm(text)
    for raw,display in PET_SUPPLIES.items():
        if raw in n:return display
    return None


def _find_referenced(entities,text):
    n=_norm(text)
    for entity in entities:
        name=str(entity.get("name") or "").strip()
        if name and re.search(r"\b"+re.escape(_norm(name))+r"\b",n): return entity
    return None


def _pets(entities): return [e for e in entities if e.get("kind")=="pet"]


async def _create_pet_reminder(db,uid,pet,item,due_date,due_time):
    title=f"Comprar {item} para {pet}"
    await db.prepare("INSERT INTO daily_items(user_id,kind,title,due_date,due_time,status) VALUES(?,'tarefa',?,?,?,'pendente')").bind(uid,title,due_date.isoformat(),due_time).run()


async def _handle_pending_time(db,token,chat_id,uid,text):
    state=await v2._last_state(db,uid)
    if not state or state.get("kind")!="pet_reminder_time": return False
    tm=parse_time(text)
    if not tm: return False
    payload=state.get("payload") or {}
    try:
        from datetime import date
        due=date.fromisoformat(payload["due_date"])
    except Exception:
        await v2._save_state(db,uid,"idle",{}); return False
    await _create_pet_reminder(db,uid,payload.get("pet") or "meu pet",payload.get("item") or "ração",due,tm)
    await v2._save_state(db,uid,"idle",{})
    await send_message(token,chat_id,f"Fechado. Te lembro às {tm} de comprar {payload.get('item') or 'ração'} para {payload.get('pet') or 'o cidadão'}. A logística felina agradece; o financeiro provavelmente não.")
    return True


async def handle_message(db, token, message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None or OWNER_CHAT_ID is None or int(chat_id)!=int(OWNER_CHAT_ID): return False
    text=(message.get("text") or "").strip()
    if not text:return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False

    if await _handle_pending_time(db,token,int(chat_id),uid,text): return True

    n=_norm(text); entities=await _entities(db,uid); pets=_pets(entities)

    if ("qual" in n or "como" in n or "lembra" in n) and "nome" in n and any(x in n for x in ("meu gato","minha gata","meu cachorro","meu pet")):
        if not pets:
            await send_message(token,int(chat_id),"Ainda não tenho nenhum pet seu registrado. Se você já me contou antes, foi antes dessa memória entrar em serviço — a burocracia chegou tarde."); return True
        names=", ".join(str(p.get("name")) for p in pets)
        await send_message(token,int(chat_id),f"Tenho sim: {names}. Pelo menos nome de funcionário eu consigo manter no cadastro."); return True

    if "qual" in n and "cor" in n and any(x in n for x in ("gato","gata","cachorro","pet")):
        target=_find_referenced(pets,text) or (pets[0] if len(pets)==1 else None)
        if target and target.get("color"):
            await send_message(token,int(chat_id),f"{target.get('name')} é {target.get('color')}. Essa parte eu guardei — ficha cadastral do cidadão está em dia."); return True

    item=_supply(text)
    reminder=any(x in n for x in ("me lembra","me lembre","pode me lembrar","lembra eu","tenho que lembrar","nao posso esquecer"))
    if item and reminder:
        referenced=_find_referenced(pets,text)
        if not referenced and any(x in n for x in ("meu gato","minha gata","meu cachorro","meu pet")) and len(pets)==1: referenced=pets[0]
        pet_name=(referenced or {}).get("name") or "meu pet"
        due=parse_date(text,ai._now().date())
        if not due:return False
        tm=parse_time(text)
        if tm:
            await _create_pet_reminder(db,uid,pet_name,item,due,tm)
            await send_message(token,int(chat_id),f"Anotado. Em {due.strftime('%d/%m')} às {tm} eu te lembro da {item} de {pet_name}. Mais uma obrigação porque o bonito decidiu terceirizar o estoque."); return True
        await v2._save_state(db,uid,"pet_reminder_time",{"pet":pet_name,"item":item,"due_date":due.isoformat()})
        await send_message(token,int(chat_id),f"Posso. {pet_name} aparentemente já trabalha com previsão de desabastecimento. Que horas em {due.strftime('%d/%m')} você quer que eu te lembre de comprar {item}?"); return True

    declared=_pet_declaration(text)
    if declared:
        color=_color(text)
        if color: declared["color"]=color
        await _save_entity(db,uid,declared)
        name=declared["name"]; species=declared["species"]
        if color:
            await send_message(token,int(chat_id),f"Peraí, então {name} é seu {species} e ainda é {color}? Certo. Mais um laranja nessa firma. Vou guardar o nome do cidadão, porque claramente ele ainda vai aparecer nos relatórios.")
        else:
            await send_message(token,int(chat_id),f"Anotado: {name} é seu {species}. Funcionário de quatro patas também entra no cadastro informal da firma.")
        return True

    referenced=_find_referenced(entities,text)
    if not referenced:return False
    if referenced.get("kind")=="pet":
        name=referenced.get("name"); species=referenced.get("species") or "pet"; item=_supply(text)
        supply_problem=item and any(x in n for x in ("sem ","acabou","ta sem","falta","faltando","precisa","comprar"))
        if supply_problem:
            await v2._save_state(db,uid,"confirm_pet_supply",{"item":item,"pet":name})
            await send_message(token,int(chat_id),f"Ah, {name}. O {species} oficialmente reconhecido pela firma já está cobrando abastecimento. Posso colocar {item} na lista. Pra você é obrigação; pra {name}, direito adquirido. Anoto?"); return True
        if any(x in n for x in ("aprontou","derrubou","quebrou","doido","maluco","danado")):
            await send_message(token,int(chat_id),f"Claro que foi {name}. O cidadão já está construindo histórico próprio. O que o {species} aprontou agora?"); return True
    return False
