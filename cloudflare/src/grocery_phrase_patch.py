import re
import unicodedata

from telegram_api import send_message

GROCERY_KB = [["➕ Adicionar item", "📋 Ver itens faltando"], ["🏠 Menu principal"]]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9, ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


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


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


def _split_items(raw):
    raw = re.sub(r"^(?:o|a|os|as)\s+", "", raw.strip())
    raw = re.sub(r"\s+(?:acabou|acabaram|acabo|cabou|cabo|ta acabando|esta acabando|acabando|nao tem mais|nao temos mais)$", "", raw).strip()
    return [x.strip() for x in re.split(r",|\s+e\s+", raw) if x.strip()]


async def handle_message(db, token, message):
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return False

    text = (message.get("text") or "").strip()
    n = _norm(text)
    if not n:
        return False

    raw_items = None

    # Verbo antes do item: "acabou o café", "cabô arroz e feijão".
    m = re.match(r"^(?:acabou|acabo|cabou|cabo)\s+(?:o|a|os|as\s+)?(.+)$", n)
    if m:
        raw_items = m.group(1)

    # Item antes do verbo: "ovo acabou", "ovos acabaram", "café tá acabando".
    if raw_items is None:
        m = re.match(r"^(.+?)\s+(?:acabou|acabaram|acabo|cabou|cabo|ta acabando|esta acabando)$", n)
        if m:
            raw_items = m.group(1)

    # Outras formas coloquiais com item primeiro.
    if raw_items is None:
        m = re.match(r"^(.+?)\s+(?:nao tem mais|nao temos mais)$", n)
        if m:
            raw_items = m.group(1)

    if raw_items is None:
        return False

    items = _split_items(raw_items)
    if not items:
        return False

    uid = await _uid(db, int(chat_id))
    if not uid:
        return False

    for item in items:
        await db.prepare(
            "INSERT INTO grocery_items(user_id,name,missing) VALUES(?,?,1) "
            "ON CONFLICT(user_id,name) DO UPDATE SET missing=1,updated_at=CURRENT_TIMESTAMP"
        ).bind(uid, item).run()

    if len(items) == 1:
        msg = f"🛒 Anotado: {items[0]}. Acabou, entrou na lista. Uma tragédia doméstica a menos para depender da memória. 😌"
    else:
        msg = "🛒 Anotado: " + ", ".join(items) + ". A despensa abriu chamado e eu registrei. 😏"

    await send_message(token, int(chat_id), msg, reply_markup=_kb(GROCERY_KB))
    return True
