import re
import unicodedata

import companion_nlu_v2 as v2
from core_actions import add_grocery_items
from deterministic_memory import _entities
from telegram_api import send_message

PETS=("gato","gata","cachorro","cachorra","cao","cão","dog","pet")
PET_FOOD=("racao","ração","sache","sachê","areia","petisco")
BUY_WORDS=("comprar","compra","preciso de","tenho de","tenho que","falta","acabou","ta acabando","tá acabando","sem")
OBLIGATION_WORDS=("tenho que","tenho de","preciso","nao posso esquecer","não posso esquecer","lembrar")

def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower()); value="".join(ch for ch in value if not unicodedata.combining(ch)); value=re.sub(r"[^a-z0-9 ]+"," ",value); return re.sub(r"\s+"," ",value).strip()
def _contains(n,values):return any(_norm(v) in n for v in values)
def _pet_name(text):
    m=re.search(r"(?:gato|gata|cachorro|cachorra)\s+(?:chamad[oa]\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{1,30})",text or ""); return m.group(1) if m else None
def _pet_item(n):
    for item in PET_FOOD:
        ni=_norm(item)
        if ni in n:return "ração" if ni=="racao" else "sachê" if ni=="sache" else item
    return None

def _species_match(entity,n):
    if entity.get("kind")!="pet":return False
    species=_norm(entity.get("species") or "")
    if "gato" in n or "gata" in n:return species in ("gato","gata")
    if any(x in n for x in ("cachorro","cachorra","cao","dog")):return species in ("cachorro","cachorra","cao")
    return True

async def _resolve_pet(db,uid,text,n):
    explicit=_pet_name(text)
    if explicit:return explicit
    pets=[e for e in await _entities(db,uid) if _species_match(e,n)]
    if len(pets)==1:return pets[0].get("name")
    return None

async def _handle_pending(db,token,chat_id,uid,text):
    state=await v2._last_state(db,uid)
    if not state or state.get("kind")!="confirm_pet_supply":return False
    n=_norm(text); payload=state.get("payload") or {}
    if v2._is_no(n):
        await v2._save_state(db,uid,"idle",{}); await send_message(token,chat_id,"Fechado. Não anotei nada. Se o cidadão de quatro patas abrir reclamação, meu nome fica fora."); return True
    if v2._is_yes(n):
        item=payload.get("item") or "ração"; saved=await add_grocery_items(db,uid,[item]); await v2._save_state(db,uid,"idle",{}); pet=payload.get("pet") or "o fiscal de quatro patas"
        if saved:await send_message(token,chat_id,f"Anotado: {saved[0]} entrou na lista. {str(pet).capitalize()} ganhou prioridade logística.")
        else:await send_message(token,chat_id,"Não consegui validar o item, então não mexi na lista.")
        return True
    return False

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    text=(message.get("text") or "").strip()
    if not text:return False
    if await _handle_pending(db,token,int(chat_id),uid,text):return True

    n=_norm(text); has_pet=_contains(n,PETS); item=_pet_item(n); has_buy=_contains(n,BUY_WORDS) or _contains(n,OBLIGATION_WORDS)
    if not (has_pet and item and has_buy):return False

    resolved=await _resolve_pet(db,uid,text,n)
    pet=resolved or ("o gato" if "gato" in n or "gata" in n else "o cachorro" if any(x in n for x in ("cachorro","cachorra","cao","dog")) else "o pet")
    await v2._save_state(db,uid,"confirm_pet_supply",{"item":item,"pet":pet})
    if resolved:intro=f"Justo. {resolved} não tem culpa da gestão de estoque."
    elif "tenho um gato" in n or "tenho uma gata" in n or "adotei" in n:intro=f"Peraí, temos {pet} na equipe agora?"
    else:intro=f"Entendi o problema do {pet}."
    await send_message(token,int(chat_id),intro+f" Quer que eu coloque {item} na lista de itens faltando? Anoto só se você confirmar.")
    return True
