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


async def _rows(stmt):
    result = await stmt.all()
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


def _split_items(raw):
    raw = re.sub(r"^(?:o|a|os|as)\s+", "", raw.strip())
    raw = re.sub(r"\s+(?:acabou|acabaram|acabo|cabou|cabo|ta acabando|esta acabando|acabando|nao tem mais|nao temos mais)$", "", raw).strip()
    return [x.strip() for x in re.split(r",|\s+e\s+", raw) if x.strip()]


async def _mark_bought(db, uid, requested_items):
    missing = await _rows(db.prepare(
        "SELECT id,name FROM grocery_items WHERE user_id=? AND missing=1 ORDER BY name"
    ).bind(uid))

    bought = []
    not_found = []
    used_ids = set()

    for requested in requested_items:
        target = _norm(requested)
        candidates = []
        for row in missing:
            rid = int(_row(row, "id"))
            if rid in used_ids:
                continue
            name = _norm(_row(row, "name") or "")
            if target == name:
                candidates = [row]
                break
            if target and name and (target in name or name in target):
                candidates.append(row)

        if len(candidates) == 1:
            row = candidates[0]
            rid = int(_row(row, "id"))
            await db.prepare(
                "UPDATE grocery_items SET missing=0,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?"
            ).bind(rid, uid).run()
            used_ids.add(rid)
            bought.append(_row(row, "name"))
        else:
            not_found.append(requested)

    return bought, not_found


async def handle_message(db, token, message):
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return False

    text = (message.get("text") or "").strip()
    n = _norm(text)
    if not n:
        return False

    uid = await _uid(db, int(chat_id))
    if not uid:
        return False

    # Compra concluída: "comprei café, açúcar e detergente".
    bought_match = re.match(
        r"^(?:ja\s+)?(?:comprei|compramos|peguei|pegamos|trouxe|trouxemos)\s+(?:o|a|os|as\s+)?(.+)$",
        n,
    )
    if bought_match:
        requested = _split_items(bought_match.group(1))
        if not requested:
            return False
        bought, not_found = await _mark_bought(db, uid, requested)

        if bought and not not_found:
            if len(bought) == 1:
                msg = f"✅ {bought[0]} saiu da lista. Uma vitória modesta contra o caos doméstico. 😌"
            else:
                msg = "✅ Comprados e retirados da lista: " + ", ".join(bought) + ". Olha só, logística funcionando sem reunião. 😏"
        elif bought:
            msg = "✅ Tirei da lista: " + ", ".join(bought) + ".\n\n🤨 Não achei com segurança: " + ", ".join(not_found) + ". Esses continuam como estavam para eu não inventar compra que você não registrou."
        else:
            msg = "🤨 Entendi que você comprou " + ", ".join(requested) + ", mas não achei esses itens na lista de faltantes. Não vou apagar coisa no chute."

        await send_message(token, int(chat_id), msg, reply_markup=_kb(GROCERY_KB))
        return True

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

    # Pedido direto de compra: "comprar milho de pipoca", "comprar café e açúcar".
    if raw_items is None:
        m = re.match(r"^(?:comprar|compra|compre)\s+(?:o|a|os|as\s+)?(.+)$", n)
        if m:
            raw_items = m.group(1)

    if raw_items is None:
        return False

    items = _split_items(raw_items)
    if not items:
        return False

    for item in items:
        await db.prepare(
            "INSERT INTO grocery_items(user_id,name,missing) VALUES(?,?,1) "
            "ON CONFLICT(user_id,name) DO UPDATE SET missing=1,updated_at=CURRENT_TIMESTAMP"
        ).bind(uid, item).run()

    if len(items) == 1:
        msg = f"🛒 Anotado: {items[0]}. Entrou na lista. Porque aparentemente até a pipoca agora precisa de gestão de estoque. 😌"
    else:
        msg = "🛒 Anotado: " + ", ".join(items) + ". A despensa abriu chamado e eu registrei. 😏"

    await send_message(token, int(chat_id), msg, reply_markup=_kb(GROCERY_KB))
    return True
