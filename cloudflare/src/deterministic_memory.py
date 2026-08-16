import json
import re
import unicodedata

import academic_intelligence as ai
import companion_nlu_v2 as v2
from nlu import parse_date, parse_time
from telegram_api import send_message

PET_SPECIES = ("gato", "gata", "cachorro", "cachorra", "cao", "cão")
PET_SUPPLIES = {"racao": "ração", "sache": "sachê", "areia": "areia", "petisco": "petisco"}
COLORS = ("laranja", "preto", "preta", "branco", "branca", "cinza", "marrom", "rajado", "rajada")
INVALID_NAMES = {"deve","vai","esta","está","ta","tá","tem","fica","ficar","ficou","anda","vive","precisa","preciso","quer","pode","podem","ele","ela","que","sem","com","tambem","também","meio","muito","um","uma"}


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
            merged = dict(data); merged.update({k:v for k,v in entity.items() if v not in (None,"",[])})
            await db.prepare("UPDATE natural_events SET detail=? WHERE id=?").bind(json.dumps(merged, ensure_ascii=False), _row(row,"id")).run(); return
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'personal_entity',?)").bind(uid,json.dumps(entity,ensure_ascii=False)).run()


async def _delete_entity(db, uid, name):
    rows=await _rows(db.prepare("SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='personal_entity' ORDER BY id DESC LIMIT 80").bind(uid))
    target=_norm(name); removed=False
    for row in rows:
        try: data=json.loads(_row(row,"detail") or "{}")
        except Exception: continue
        if _norm(data.get("name") or "")==target:
            await db.prepare("DELETE FROM natural_events WHERE id=? AND user_id=?").bind(_row(row,"id"),uid).run(); removed=True
    return removed


async def _entities(db, uid):
    rows=await _rows(db.prepare("SELECT detail FROM natural_events WHERE user_id=? AND event_type='personal_entity' ORDER BY id DESC LIMIT 80").bind(uid)); out=[]; seen=set()
    for row in rows:
        try: data=json.loads(_row(row,"detail") or "{}")
        except Exception: continue
        name=str(data.get("name") or "").strip(); key=_norm(name)
        if name and key not in seen: seen.add(key); out.append(data)
    return out


def _valid_name(name):
    n=_norm(name); return bool(n and n not in INVALID_NAMES and len(n)>=2)


def _pet_declaration(text):
    patterns=[
        r"(?:tenho|adotei|peguei)\s+(?:um|uma)\s+(gato|gata|cachorro|cachorra|cao|cão)\s+(?:chamad[oa]\s+)?([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})",
        r"meu\s+(gato|gata|cachorro|cachorra|cao|cão)\s+(?:chamad[oa]\s+)([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})",
        r"([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})\s+(?:e|é)\s+(?:o\s+|a\s+)?meu\s+(gato|gata|cachorro|cachorra|cao|cão)"]
    for index,pattern in enumerate(patterns):
        m=re.search(pattern,text or "",flags=re.I)
        if not m: continue
        species,name=(m.group(1),m.group(2)) if index<2 else (m.group(2),m.group(1))
        if _valid_name(name): return {"kind":"pet","name":name.capitalize(),"species":_norm(species)}
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
    await db.prepare("INSERT INTO daily_items(user_id,kind,title,due_date,due_time,status) VALUES(?,'tarefa',?,?,?,'pendente')").bind(uid,f"Comprar {item} para {pet}",due_date.isoformat(),due_time).run()


async def _handle_pending_time(db,token,chat_id,uid,text):
    state=await v2._last_state(db,uid)
    if not state or state.get("kind")!="pet_reminder_time": return False
    tm=parse_time(text)
    if not tm:return False
    payload=state.get("payload") or {}
    try:
        from datetime import date
        due=date.fromisoformat(payload["due_date"])
    except Exception:
        await v2._save_state(db,uid,"idle",{}); return False
    await _create_pet_reminder(db,uid,payload.get("pet") or "meu pet",payload.get("item") or "ração",due,tm); await v2._save_state(db,uid,"idle",{})
    await send_message(token,chat_id,f"Fechado. Te lembro às {tm} de comprar {payload.get('item') or 'ração'} para {payload.get('pet') or 'o cidadão'}."); return True


async def handle_message(db, token, message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None: return False
    text=(message.get("text") or "").strip()
    if not text:return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    if await _handle_pending_time(db,token,int(chat_id),uid,text): return True

    n=_norm(text); entities=await _entities(db,uid); pets=_pets(entities)

    correction=re.search(r"(?:apaga|apague|remove|remova|esquece|esqueça)\s+(?:o\s+)?([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})",text,flags=re.I)
    corrected=re.search(r"(?:nome do meu gato|meu gato)\s+(?:e|é|se chama)\s+([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})",text,flags=re.I)
    if correction:
        old=correction.group(1); removed=await _delete_entity(db,uid,old)
        if corrected and _valid_name(corrected.group(1)):
            new=corrected.group(1).capitalize(); await _save_entity(db,uid,{"kind":"pet","name":new,"species":"gato"})
            await send_message(token,int(chat_id),f"Corrigido. Apaguei {old} da memória e deixei {new} como seu gato."); return True
        await send_message(token,int(chat_id),f"{'Apaguei '+old+' da memória.' if removed else old+' não estava na minha memória.'}"); return True

    if corrected and _valid_name(corrected.group(1)):
        new=corrected.group(1).capitalize(); await _save_entity(db,uid,{"kind":"pet","name":new,"species":"gato"})
        await send_message(token,int(chat_id),f"Anotado: seu gato é {new}."); return True

    if ("qual" in n or "como" in n or "lembra" in n) and "nome" in n and any(x in n for x in ("meu gato","minha gata","meu cachorro","meu pet")):
        if not pets: await send_message(token,int(chat_id),"Ainda não tenho nenhum pet seu registrado."); return True
        names=", ".join(str(p.get("name")) for p in pets); await send_message(token,int(chat_id),f"Tenho sim: {names}."); return True

    referenced=_find_referenced(entities,text)
    if referenced and ("quem e" in n or "quem eh" in n or ("lembra" in n and "quem" in n)):
        if referenced.get("kind")=="pet":
            extra=f" e é {referenced.get('color')}" if referenced.get("color") else ""
            await send_message(token,int(chat_id),f"Lembro. {referenced.get('name')} é seu {referenced.get('species') or 'pet'}{extra}."); return True

    if "qual" in n and "cor" in n and any(x in n for x in ("gato","gata","cachorro","pet")):
        target=referenced or (pets[0] if len(pets)==1 else None)
        if target and target.get("color"): await send_message(token,int(chat_id),f"{target.get('name')} é {target.get('color')}."); return True

    item=_supply(text); reminder=any(x in n for x in ("me lembra","me lembre","pode me lembrar","lembra eu","tenho que lembrar","nao posso esquecer"))
    if item and reminder:
        if not referenced and any(x in n for x in ("meu gato","minha gata","meu cachorro","meu pet")) and len(pets)==1: referenced=pets[0]
        pet_name=(referenced or {}).get("name") or "meu pet"; due=parse_date(text,ai._now().date())
        if not due:return False
        tm=parse_time(text)
        if tm:
            await _create_pet_reminder(db,uid,pet_name,item,due,tm); await send_message(token,int(chat_id),f"Anotado. Em {due.strftime('%d/%m')} às {tm} eu te lembro da {item} de {pet_name}."); return True
        await v2._save_state(db,uid,"pet_reminder_time",{"pet":pet_name,"item":item,"due_date":due.isoformat()}); await send_message(token,int(chat_id),f"Posso. Que horas em {due.strftime('%d/%m')} você quer que eu te lembre de comprar {item} para {pet_name}?"); return True

    declared=_pet_declaration(text)
    if declared:
        color=_color(text)
        if color:declared["color"]=color
        await _save_entity(db,uid,declared); name=declared["name"]; species=declared["species"]
        await send_message(token,int(chat_id),f"Anotado: {name} é seu {species}"+(f" e é {color}." if color else ".")); return True

    if not referenced:return False
    if referenced.get("kind")=="pet":
        name=referenced.get("name"); item=_supply(text)
        if item and any(x in n for x in ("sem ","acabou","ta sem","falta","faltando","precisa","comprar")):
            await v2._save_state(db,uid,"confirm_pet_supply",{"item":item,"pet":name}); await send_message(token,int(chat_id),f"Ah, {name}. Posso colocar {item} na lista. Anoto?"); return True
        if any(x in n for x in ("aprontou","derrubou","quebrou","doido","maluco","danado")):
            await send_message(token,int(chat_id),f"Claro que foi {name}. O que o cidadão aprontou agora?"); return True
    return False
