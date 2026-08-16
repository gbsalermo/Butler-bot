import json
import re
import unicodedata

import companion_nlu_v2 as v2
from deterministic_memory import _entities, _find_referenced, _save_entity, _delete_entity
from telegram_api import send_message

RELATIONS = {
    "mae":"mãe", "mãe":"mãe", "pai":"pai", "irma":"irmã", "irmã":"irmã", "irmao":"irmão", "irmão":"irmão",
    "avo":"avó", "avó":"avó", "avô":"avô", "tia":"tia", "tio":"tio", "prima":"prima", "primo":"primo",
    "amiga":"amiga", "amigo":"amigo", "colega":"colega", "namorada":"namorada", "namorado":"namorado",
    "esposa":"esposa", "marido":"marido", "ficante":"ficante"
}
VEHICLES=("carro","moto","motocicleta","bicicleta","bike")
OBJECTS=("notebook","celular","telefone","pc","computador","tablet","camera","câmera","violao","violão","guitarra")
INVALID={"deve","vai","tem","fica","ficar","esta","está","ta","tá","que","ele","ela","com","sem","meu","minha"}


def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    value=re.sub(r"[^a-z0-9 ]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()


def _valid(value):
    n=_norm(value)
    return bool(n and n not in INVALID and len(n)>=2)


def _person_declaration(text):
    # "minha mãe se chama Ana", "tenho um amigo chamado Lucas", "Marcos é meu colega"
    m=re.search(r"minh[ao]\s+(mae|mãe|pai|irma|irmã|irmao|irmão|avo|avó|avô|tia|tio|prima|primo|namorada|namorado|esposa|marido|ficante)\s+(?:se chama|chama|é|e)\s+([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,40})",text,flags=re.I)
    if m and _valid(m.group(2)):
        rel=RELATIONS.get(_norm(m.group(1)),_norm(m.group(1)))
        return {"kind":"person","name":m.group(2).capitalize(),"relation":rel}
    m=re.search(r"tenho\s+(?:um|uma)\s+(amigo|amiga|colega|namorado|namorada|ficante)\s+(?:chamad[oa]\s+)?([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,40})",text,flags=re.I)
    if m and _valid(m.group(2)):
        return {"kind":"person","name":m.group(2).capitalize(),"relation":RELATIONS.get(_norm(m.group(1)),_norm(m.group(1)))}
    m=re.search(r"([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,40})\s+(?:e|é)\s+(?:meu|minha)\s+(amigo|amiga|colega|namorado|namorada|ficante|mae|mãe|pai|irma|irmã|irmao|irmão)",text,flags=re.I)
    if m and _valid(m.group(1)):
        return {"kind":"person","name":m.group(1).capitalize(),"relation":RELATIONS.get(_norm(m.group(2)),_norm(m.group(2)))}
    return None


def _thing_declaration(text):
    n=_norm(text)
    for label in VEHICLES:
        m=re.search(rf"meu\s+{re.escape(label)}\s+(?:e|é)\s+(?:um\s+|uma\s+)?(.{{2,70}})$",text,flags=re.I)
        if m:
            model=m.group(1).strip(" .,!?")
            if _valid(model): return {"kind":"vehicle","name":label,"label":label,"model":model}
    for label in OBJECTS:
        m=re.search(rf"meu\s+{re.escape(label)}\s+(?:e|é)\s+(?:um\s+|uma\s+)?(.{{2,70}})$",text,flags=re.I)
        if m:
            model=m.group(1).strip(" .,!?")
            if _valid(model): return {"kind":"object","name":label,"label":label,"model":model}
    return None


def _relation_query(n):
    for raw,rel in RELATIONS.items():
        if raw in n and any(x in n for x in ("qual o nome","qual nome","como chama","quem e","quem é")):
            return rel
    return None


def _describe(entity):
    kind=entity.get("kind")
    if kind=="person": return f"{entity.get('name')} é {entity.get('relation') or 'uma pessoa conhecida'} seu/sua."
    if kind=="vehicle": return f"Seu {entity.get('label') or 'veículo'} é {entity.get('model') or entity.get('name')}."
    if kind=="object": return f"Seu {entity.get('label') or 'objeto'} é {entity.get('model') or entity.get('name')}."
    return None


async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=_norm(text); entities=await _entities(db,uid)

    # Correção/remoção simples e explícita: "esquece Lucas" / "apaga meu carro".
    m=re.search(r"(?:esquece|esqueça|apaga|apague|remove|remova)\s+(?:que\s+)?(?:o\s+|a\s+)?([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{2,40})",text,flags=re.I)
    if m:
        target=m.group(1)
        if await _delete_entity(db,uid,target):
            await send_message(token,int(chat_id),f"Fechado. Tirei {target} da memória."); return True

    declared=_person_declaration(text) or _thing_declaration(text)
    if declared:
        await _save_entity(db,uid,declared)
        if declared["kind"]=="person":
            await send_message(token,int(chat_id),f"Anotado. {declared['name']} é {declared['relation']} seu/sua. Se essa pessoa voltar pra conversa, eu já sei de quem estamos falando."); return True
        await send_message(token,int(chat_id),f"Anotado. Seu {declared['label']} é {declared['model']}. Mais um item oficialmente incorporado ao patrimônio da firma."); return True

    relation=_relation_query(n)
    if relation:
        matches=[e for e in entities if e.get("kind")=="person" and e.get("relation")==relation]
        if len(matches)==1:
            await send_message(token,int(chat_id),f"{matches[0].get('name')}. Tenho registrado como {relation} seu/sua."); return True
        if len(matches)>1:
            names=", ".join(e.get("name") for e in matches)
            await send_message(token,int(chat_id),f"Tenho mais de uma pessoa nessa relação: {names}."); return True

    for label in VEHICLES+OBJECTS:
        if label in n and any(x in n for x in ("qual","que","o que sabe","lembra")):
            matches=[e for e in entities if e.get("label")==label]
            if len(matches)==1:
                await send_message(token,int(chat_id),_describe(matches[0])); return True

    referenced=_find_referenced(entities,text)
    if referenced and any(x in n for x in ("quem e","quem é","o que sabe sobre","voce lembra","você lembra","lembra de")):
        desc=_describe(referenced)
        if desc:
            await send_message(token,int(chat_id),desc); return True

    return False
