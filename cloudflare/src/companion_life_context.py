import re
import unicodedata

import companion_nlu_v2 as v2
from settings import OWNER_CHAT_ID
from telegram_api import send_message

PETS = ("gato", "gata", "cachorro", "cachorra", "cao", "cão", "dog", "pet")
PET_FOOD = ("racao", "ração", "sache", "sachê", "areia", "petisco")
BUY_WORDS = ("comprar", "compra", "preciso de", "tenho de", "tenho que", "falta", "acabou", "ta acabando", "tá acabando")
OBLIGATION_WORDS = ("tenho que", "tenho de", "preciso", "nao posso esquecer", "não posso esquecer", "lembrar")


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _contains(n, values):
    return any(_norm(v) in n for v in values)


def _pet_name(text):
    # Ex.: "meu gato Tobias", "tenho uma gata chamada Luna".
    m = re.search(r"(?:gato|gata|cachorro|cachorra)\s+(?:chamad[oa]\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç-]{1,30})", text or "")
    return m.group(1) if m else None


def _pet_item(n):
    for item in PET_FOOD:
        ni = _norm(item)
        if ni in n:
            if ni == "racao":
                return "ração"
            if ni == "sache":
                return "sachê"
            return item
    return None


async def _add_grocery(db, uid, item):
    existing = await db.prepare("SELECT id FROM grocery_items WHERE user_id=? AND lower(name)=lower(?) LIMIT 1").bind(uid, item).first()
    if existing:
        await db.prepare("UPDATE grocery_items SET missing=1,updated_at=CURRENT_TIMESTAMP WHERE id=?").bind(v2._row(existing, "id")).run()
        return False
    await db.prepare("INSERT INTO grocery_items(user_id,name,missing) VALUES(?,?,1)").bind(uid, item).run()
    return True


async def _handle_pending(db, token, chat_id, uid, text):
    state = await v2._last_state(db, uid)
    if not state or state.get("kind") != "confirm_pet_supply":
        return False
    n = _norm(text)
    payload = state.get("payload") or {}
    if v2._is_no(n):
        await v2._save_state(db, uid, "idle", {})
        await send_message(token, chat_id, "Fechado. Não anotei nada. Mas se o cidadão de quatro patas reclamar, meu nome fica fora dessa investigação.")
        return True
    if v2._is_yes(n):
        item = payload.get("item") or "ração"
        created = await _add_grocery(db, uid, item)
        await v2._save_state(db, uid, "idle", {})
        pet = payload.get("pet") or "o fiscal de quatro patas"
        if created:
            await send_message(token, chat_id, f"Anotado: {item} entrou na lista. {pet.capitalize()} ganhou prioridade logística. Mais uma obrigação no seu currículo, chefe — pelo menos essa ronrona ou abana o rabo.")
        else:
            await send_message(token, chat_id, f"{item.capitalize()} já estava na lista; marquei como faltando de novo. {pet.capitalize()} claramente tem um setor de cobrança melhor organizado que o seu.")
        return True
    return False


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None or OWNER_CHAT_ID is None or int(chat_id) != int(OWNER_CHAT_ID):
        return False
    uid = await v2._uid(db, int(chat_id))
    if not uid:
        return False
    text = (message.get("text") or "").strip()
    if not text:
        return False

    if await _handle_pending(db, token, int(chat_id), uid, text):
        return True

    n = _norm(text)
    has_pet = _contains(n, PETS)
    item = _pet_item(n)
    has_buy = _contains(n, BUY_WORDS) or _contains(n, OBLIGATION_WORDS)
    if not (has_pet and item and has_buy):
        return False

    name = _pet_name(text)
    pet = name or ("o gato" if "gato" in n or "gata" in n else "o cachorro")
    await v2._save_state(db, uid, "confirm_pet_supply", {"item": item, "pet": pet})

    if "tenho um gato" in n or "tenho uma gata" in n or "adotei" in n or "peguei um gato" in n:
        intro = f"Peraí, temos {pet} na equipe agora? Informação importante que aparentemente o RH felino esqueceu de me passar."
    else:
        intro = f"Justo. {pet.capitalize()} não tem culpa da sua gestão de estoque."
    await send_message(token, int(chat_id), intro + f" Posso colocar {item} na lista de compras. Mais uma obrigação pra sua coleção, mas essa pelo menos vem com pelos e julgamento silencioso. Anoto?")
    return True
