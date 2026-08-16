import json
import re
import unicodedata

import companion_nlu_v2 as v2
from settings import OWNER_CHAT_ID
from telegram_api import send_message

PET_SPECIES = ("gato", "gata", "cachorro", "cachorra", "cao", "cão")
PET_SUPPLIES = {
    "racao": "ração",
    "sache": "sachê",
    "areia": "areia",
    "petisco": "petisco",
}
COLORS = ("laranja", "preto", "preta", "branco", "branca", "cinza", "marrom", "rajado", "rajada")


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


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


async def _save_entity(db, uid, entity):
    name = str(entity.get("name") or "").strip()
    if not name:
        return
    existing = await _rows(db.prepare(
        "SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='personal_entity' ORDER BY id DESC LIMIT 80"
    ).bind(uid))
    target = _norm(name)
    for row in existing:
        try:
            data = json.loads(_row(row, "detail") or "{}")
        except Exception:
            continue
        if _norm(data.get("name") or "") == target:
            merged = dict(data)
            for key, value in entity.items():
                if value not in (None, "", []):
                    merged[key] = value
            await db.prepare("UPDATE natural_events SET detail=? WHERE id=?").bind(
                json.dumps(merged, ensure_ascii=False), _row(row, "id")
            ).run()
            return
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'personal_entity',?)").bind(
        uid, json.dumps(entity, ensure_ascii=False)
    ).run()


async def _entities(db, uid):
    rows = await _rows(db.prepare(
        "SELECT detail FROM natural_events WHERE user_id=? AND event_type='personal_entity' ORDER BY id DESC LIMIT 80"
    ).bind(uid))
    out = []
    seen = set()
    for row in rows:
        try:
            data = json.loads(_row(row, "detail") or "{}")
        except Exception:
            continue
        name = str(data.get("name") or "").strip()
        key = _norm(name)
        if name and key not in seen:
            seen.add(key)
            out.append(data)
    return out


def _pet_declaration(text):
    # "tenho um gato chamado Jake", "meu gato Jake", "Jake é meu gato".
    patterns = [
        r"(?:tenho|adotei|peguei)\s+(?:um|uma)\s+(gato|gata|cachorro|cachorra|cao|cão)\s+(?:chamad[oa]\s+)?([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})",
        r"meu\s+(gato|gata|cachorro|cachorra|cao|cão)\s+(?:chamad[oa]\s+)?([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})",
        r"([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,30})\s+(?:e|é)\s+(?:o\s+|a\s+)?meu\s+(gato|gata|cachorro|cachorra|cao|cão)",
    ]
    for index, pattern in enumerate(patterns):
        m = re.search(pattern, text or "", flags=re.I)
        if not m:
            continue
        if index < 2:
            species, name = m.group(1), m.group(2)
        else:
            name, species = m.group(1), m.group(2)
        # Evita capturar conectivos como nome em frases incompletas.
        if _norm(name) in {"que", "ele", "ela", "tambem", "também"}:
            continue
        return {"kind": "pet", "name": name.capitalize(), "species": _norm(species)}
    return None


def _color(text):
    n = _norm(text)
    for color in COLORS:
        if _norm(color) in n:
            return _norm(color)
    return None


def _supply(text):
    n = _norm(text)
    for raw, display in PET_SUPPLIES.items():
        if raw in n:
            return display
    return None


def _supply_problem(text):
    n = _norm(text)
    markers = ("sem ", "acabou", "ta sem", "tá sem", "falta", "faltando", "precisa", "preciso comprar", "comprar")
    return any(_norm(x) in n for x in markers)


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None or OWNER_CHAT_ID is None or int(chat_id) != int(OWNER_CHAT_ID):
        return False
    text = (message.get("text") or "").strip()
    if not text:
        return False
    uid = await v2._uid(db, int(chat_id))
    if not uid:
        return False

    declared = _pet_declaration(text)
    if declared:
        color = _color(text)
        if color:
            declared["color"] = color
        await _save_entity(db, uid, declared)
        name = declared["name"]
        species = declared["species"]
        if color:
            await send_message(token, int(chat_id), f"Peraí, então {name} é seu {species} e ainda é {color}? Certo. Mais um laranja nessa firma. Vou guardar o nome do cidadão, porque claramente ele ainda vai aparecer nos relatórios.")
        else:
            await send_message(token, int(chat_id), f"Anotado: {name} é seu {species}. Informação importante — funcionário de quatro patas também entra no cadastro informal da firma.")
        return True

    n = _norm(text)
    entities = await _entities(db, uid)
    referenced = None
    for entity in entities:
        name = str(entity.get("name") or "").strip()
        if name and re.search(r"\b" + re.escape(_norm(name)) + r"\b", n):
            referenced = entity
            break
    if not referenced:
        return False

    # Se mencionou uma entidade conhecida, ao menos sabemos o que ela é.
    if referenced.get("kind") == "pet":
        name = referenced.get("name")
        species = referenced.get("species") or "pet"
        item = _supply(text)
        if item and _supply_problem(text):
            await v2._save_state(db, uid, "confirm_pet_supply", {"item": item, "pet": name})
            await send_message(token, int(chat_id), f"Ah, {name}. O {species} oficialmente reconhecido pela firma já está cobrando abastecimento. Posso colocar {item} na lista de compras. Mais uma obrigação pra você, chefe; pra {name}, aparentemente é só direito adquirido. Anoto?")
            return True

        if any(x in n for x in ("aprontou", "derrubou", "quebrou", "doido", "maluco", "danado")):
            await send_message(token, int(chat_id), f"Claro que foi {name}. Eu mal terminei de registrar o cidadão e ele já começou a construir histórico próprio. O que o {species} aprontou agora?")
            return True

    return False
