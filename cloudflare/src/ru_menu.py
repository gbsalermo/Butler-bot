"""Cardápio semanal do Restaurante Universitário (RU).

Importa `.txt`, guarda o cardápio por usuário/data no D1 e responde consultas
naturais como "qual o almoço hoje?". OCR/PDF ficam fora do runtime nesta versão.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta

import app
from telegram_api import get_file_bytes, send_message


RU_KB = [
    ["🍽️ Cardápio de hoje", "📅 Cardápio da semana"],
    ["📤 Atualizar cardápio RU", "🗃️ Cardápios anteriores"],
    ["⬅️ Voltar ao cotidiano"],
]
CANCEL_KB = [["❌ Cancelar ação"]]

MEALS = {
    "cafe": ("☕", "Café / desjejum"),
    "almoco": ("🍛", "Almoço"),
    "jantar": ("🌙", "Jantar"),
}
MEAL_ALIASES = {
    "cafe da manha": "cafe",
    "desjejum": "cafe",
    "cafe": "cafe",
    "almoco": "almoco",
    "jantar": "jantar",
    "janta": "jantar",
}
DAY_ALIASES = {
    "segunda feira": 0, "segunda": 0, "seg": 0,
    "terca feira": 1, "terca": 1, "ter": 1,
    "quarta feira": 2, "quarta": 2, "qua": 2,
    "quinta feira": 3, "quinta": 3, "qui": 3,
    "sexta feira": 4, "sexta": 4, "sex": 4,
    "sabado": 5, "sab": 5,
    "domingo": 6, "dom": 6,
}
DAY_NAMES = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
DIRECT_TEXTS = {
    "🍽️ RU", "🍽️ Restaurante Universitário", "🍽️ Cardápio de hoje",
    "📅 Cardápio da semana", "📤 Atualizar cardápio RU", "🗃️ Cardápios anteriores",
}


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9:/? ]+", " ", value)).strip()


def _parse_date(value):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime((value or "").strip(), fmt).date()
        except ValueError:
            pass
    return None


def _weekday(text):
    n = _norm(text)
    for label, idx in sorted(DAY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(label)}\b", n):
            return idx
    return None


def _meal(text):
    n = _norm(text).strip(" :[]-_")
    for alias, meal in sorted(MEAL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if n == alias or n.startswith(alias + " "):
            return meal
    return None


def _week_dates(line):
    tokens = re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", line or "")
    if len(tokens) < 2:
        return None, None
    start, end = _parse_date(tokens[0]), _parse_date(tokens[1])
    return (start, end) if start and end and start <= end else (None, None)


def _heading_date(line, week_start=None):
    raw = (line or "").strip().strip("[]")
    token = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", raw)
    if token:
        return _parse_date(token.group(0))
    idx = _weekday(raw)
    if idx is None or not week_start:
        return None
    monday = week_start - timedelta(days=week_start.weekday())
    return monday + timedelta(days=idx)


def _is_day_heading(line):
    n = _norm((line or "").strip().strip("[]"))
    if not n:
        return False
    has_day = _weekday(n) is not None
    has_date = bool(re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", n))
    return (has_day and (has_date or len(n.split()) <= 5)) or (has_date and len(n.split()) <= 5)


def _item(line):
    raw = (line or "").strip().lstrip("•*- ").strip()
    if not raw:
        return None
    if ":" in raw:
        label, value = raw.split(":", 1)
    elif "|" in raw:
        label, value = raw.split("|", 1)
    else:
        parts = re.split(r"\s{2,}|\t+", raw, maxsplit=1)
        label, value = parts if len(parts) == 2 else ("Item", raw)
    if not value.strip():
        return None
    return {"label": label.strip() or "Item", "value": value.strip()}


def parse_ru_menu_text(text):
    """Parseia o formato oficial e pequenas variações comuns da conversão para TXT."""
    if not text or not text.strip():
        return None
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    week_start = week_end = None
    for line in lines[:20]:
        start, end = _week_dates(line)
        if start and end:
            week_start, week_end = start, end
            break

    days = {}
    current_date = None
    current_meal = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        period_start, period_end = _week_dates(line)
        if period_start and period_end:
            continue
        if _is_day_heading(line):
            candidate = _heading_date(line, week_start)
            if candidate:
                current_date, current_meal = candidate, None
                days.setdefault(candidate.isoformat(), {})
                continue
        meal = _meal(line)
        if meal and len(_norm(line).split()) <= 5:
            current_meal = meal
            if current_date:
                days.setdefault(current_date.isoformat(), {}).setdefault(meal, [])
            continue
        if current_date and current_meal:
            parsed = _item(line)
            if parsed:
                days[current_date.isoformat()].setdefault(current_meal, []).append(parsed)

    clean = []
    for iso in sorted(days):
        meals = {name: items for name, items in days[iso].items() if items}
        if meals:
            clean.append({"date": iso, "meals": meals})
    if not clean:
        return None

    parsed_dates = [date.fromisoformat(day["date"]) for day in clean]
    if week_start is None:
        week_start = min(parsed_dates) - timedelta(days=min(parsed_dates).weekday())
    if week_end is None:
        week_end = week_start + timedelta(days=6)
    if any(d < week_start or d > week_end for d in parsed_dates):
        return None
    return {"week_start": week_start.isoformat(), "week_end": week_end.isoformat(), "days": clean}


def _looks_ru(text):
    if text in DIRECT_TEXTS:
        return True
    n = _norm(text)
    if not n:
        return False
    if "cardapio" in n or "restaurante universitario" in n or re.search(r"\bru\b", n):
        return True
    has_date = any(x in n for x in ("hoje", "amanha", "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"))
    vegetarian = "vegetariano" in n or "vegetariana" in n
    weekly_search = "semana" in n and "dias" in n and bool(re.search(r"\btem\b", n))
    if (vegetarian and has_date) or weekly_search:
        return True
    has_meal = any(re.search(rf"\b{re.escape(alias)}\b", n) for alias in MEAL_ALIASES)
    asks = any(marker in n for marker in ("qual ", "o que ", "que tem", "vai ter", "tem ")) or n.endswith("?")
    return has_date and has_meal and asks


def _target_date(text, today):
    n = _norm(text)
    if "depois de amanha" in n:
        return today + timedelta(days=2)
    if re.search(r"\bamanha\b", n):
        return today + timedelta(days=1)
    if re.search(r"\bhoje\b", n):
        return today
    token = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\b", n)
    if token:
        try:
            return date(int(token.group(3) or today.year), int(token.group(2)), int(token.group(1)))
        except ValueError:
            return None
    idx = _weekday(n)
    if idx is not None:
        candidate = today - timedelta(days=today.weekday()) + timedelta(days=idx)
        return candidate + timedelta(days=7) if any(x in n for x in ("proxima", "proximo", "que vem")) else candidate
    return today


def _requested_meal(text):
    n = _norm(text)
    for alias, meal in sorted(MEAL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", n):
            return meal
    return None


def _keyword(text):
    n = _norm(text)
    match = re.search(
        r"\btem(?: algum| alguma)?\s+(.+?)(?=\s+(?:hoje|amanha|depois de amanha|segunda|terca|quarta|quinta|sexta|sabado|domingo|no cafe|no almoco|no jantar|na janta|no ru)\b|\?|$)",
        n,
    )
    if not match:
        return None
    value = match.group(1).strip()
    if not value or value.startswith(("no ", "na ", "para ", "pra ")) or value in {"almoco", "jantar", "janta", "cafe", "comida", "cardapio"}:
        return None
    return value


async def _ensure_schema(db):
    await db.prepare("""CREATE TABLE IF NOT EXISTS ru_menu_imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        week_start TEXT NOT NULL,
        week_end TEXT NOT NULL,
        source_filename TEXT,
        imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, week_start)
    )""").run()
    await db.prepare("""CREATE TABLE IF NOT EXISTS ru_menu_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        import_id INTEGER,
        meal_date TEXT NOT NULL,
        meal_type TEXT NOT NULL,
        item_label TEXT NOT NULL,
        item_value TEXT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(import_id) REFERENCES ru_menu_imports(id) ON DELETE SET NULL
    )""").run()
    await db.prepare("CREATE INDEX IF NOT EXISTS idx_ru_menu_user_date ON ru_menu_entries(user_id,meal_date,meal_type,position)").run()


async def _save(db, uid, parsed, filename):
    start, end = parsed["week_start"], parsed["week_end"]
    await db.prepare("""INSERT INTO ru_menu_imports(user_id,week_start,week_end,source_filename,imported_at)
        VALUES(?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(user_id,week_start) DO UPDATE SET week_end=excluded.week_end,
        source_filename=excluded.source_filename,imported_at=CURRENT_TIMESTAMP""").bind(uid, start, end, filename).run()
    row = await db.prepare("SELECT id FROM ru_menu_imports WHERE user_id=? AND week_start=?").bind(uid, start).first()
    import_id = int(app.rowget(row, "id"))
    await db.prepare("DELETE FROM ru_menu_entries WHERE user_id=? AND meal_date BETWEEN ? AND ?").bind(uid, start, end).run()
    count = 0
    for day in parsed["days"]:
        for meal, items in day["meals"].items():
            for pos, item in enumerate(items, 1):
                await db.prepare("INSERT INTO ru_menu_entries(user_id,import_id,meal_date,meal_type,item_label,item_value,position) VALUES(?,?,?,?,?,?,?)").bind(
                    uid, import_id, day["date"], meal, item["label"], item["value"], pos
                ).run()
                count += 1
    return count


async def _day_rows(db, uid, target):
    return await app.rows(db.prepare("""SELECT meal_type,item_label,item_value,position FROM ru_menu_entries
        WHERE user_id=? AND meal_date=? ORDER BY CASE meal_type WHEN 'cafe' THEN 1 WHEN 'almoco' THEN 2 WHEN 'jantar' THEN 3 ELSE 9 END,position,id""").bind(uid, target.isoformat()))


async def _range_rows(db, uid, start, end):
    return await app.rows(db.prepare("""SELECT meal_date,meal_type,item_label,item_value,position FROM ru_menu_entries
        WHERE user_id=? AND meal_date BETWEEN ? AND ? ORDER BY meal_date,CASE meal_type WHEN 'cafe' THEN 1 WHEN 'almoco' THEN 2 WHEN 'jantar' THEN 3 ELSE 9 END,position,id""").bind(uid, start.isoformat(), end.isoformat()))


def _format_day(target, rows, meal=None, vegetarian=False):
    grouped = {}
    for row in rows:
        grouped.setdefault(app.rowget(row, "meal_type"), []).append((app.rowget(row, "item_label"), app.rowget(row, "item_value")))
    parts = [f"🍽️ RU — {DAY_NAMES[target.weekday()].capitalize()}, {target.strftime('%d/%m')}"]
    for name in ([meal] if meal else ["cafe", "almoco", "jantar"]):
        items = grouped.get(name, [])
        if vegetarian:
            items = [(label, value) for label, value in items if "vegetarian" in _norm(label) or "vegano" in _norm(label)]
        if not items:
            continue
        icon, title = MEALS[name]
        block = [f"{icon} {title}"]
        for label, value in items:
            if _norm(label) == "item":
                block.append(f"• {value}")
            elif "vegetarian" in _norm(label) or "vegano" in _norm(label):
                block.append(f"🌱 {label}: {value}")
            else:
                block.append(f"• {label}: {value}")
        parts.append("\n".join(block))
    return "\n\n".join(parts) if len(parts) > 1 else None


async def _show_day(db, token, chat, uid, target, meal=None, vegetarian=False):
    text = _format_day(target, await _day_rows(db, uid, target), meal, vegetarian)
    if text:
        await send_message(token, chat, text, reply_markup=app.kb(RU_KB))
        return
    imported = await db.prepare("SELECT id FROM ru_menu_imports WHERE user_id=? AND ? BETWEEN week_start AND week_end LIMIT 1").bind(uid, target.isoformat()).first()
    msg = f"🍽️ O cardápio da semana está salvo, mas não encontrei {'essa refeição' if meal else 'esse dia'} em {target.strftime('%d/%m')}." if imported else "🍽️ Ainda não recebi o cardápio dessa semana. Use “📤 Atualizar cardápio RU” e envie o `.txt`."
    await send_message(token, chat, msg, reply_markup=app.kb(RU_KB))


async def _show_week(db, token, chat, uid, today):
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    rows = await _range_rows(db, uid, monday, sunday)
    if not rows:
        await send_message(token, chat, "🍽️ Ainda não tenho cardápio salvo para esta semana.", reply_markup=app.kb(RU_KB))
        return
    blocks = [f"📅 Cardápio RU — {monday.strftime('%d/%m')} a {sunday.strftime('%d/%m')}"]
    for iso in sorted({app.rowget(row, "meal_date") for row in rows}):
        block = _format_day(date.fromisoformat(iso), [row for row in rows if app.rowget(row, "meal_date") == iso])
        if block:
            blocks.append(block)
    chunks, current = [], ""
    for block in blocks:
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) > 3500 and current:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    for idx, chunk in enumerate(chunks):
        await send_message(token, chat, chunk, reply_markup=app.kb(RU_KB) if idx == len(chunks) - 1 else None)


async def _history(db, token, chat, uid):
    rows = await app.rows(db.prepare("SELECT week_start,week_end,source_filename FROM ru_menu_imports WHERE user_id=? ORDER BY week_start DESC LIMIT 8").bind(uid))
    if not rows:
        await send_message(token, chat, "🗃️ Ainda não há cardápios anteriores salvos.", reply_markup=app.kb(RU_KB))
        return
    out = ["🗃️ Cardápios RU salvos"]
    for row in rows:
        start, end = date.fromisoformat(app.rowget(row, "week_start")), date.fromisoformat(app.rowget(row, "week_end"))
        out.append(f"• {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')} — {app.rowget(row, 'source_filename') or 'TXT'}")
    await send_message(token, chat, "\n".join(out), reply_markup=app.kb(RU_KB))


async def _search_food(db, token, chat, uid, text, today, keyword, meal=None):
    if "semana" in _norm(text) and "dias" in _norm(text):
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        rows = await _range_rows(db, uid, start, end)
        matches = [r for r in rows if keyword in _norm(app.rowget(r, "item_value")) and (not meal or app.rowget(r, "meal_type") == meal)]
        if not matches:
            await send_message(token, chat, f"🍽️ Não achei “{keyword}” no cardápio desta semana.", reply_markup=app.kb(RU_KB))
            return
        out, seen = [f"🔎 “{keyword}” aparece nestes dias:"], set()
        for row in matches:
            key = (app.rowget(row, "meal_date"), app.rowget(row, "meal_type"), app.rowget(row, "item_value"))
            if key in seen:
                continue
            seen.add(key)
            d = date.fromisoformat(key[0])
            out.append(f"• {DAY_NAMES[d.weekday()].capitalize()} {d.strftime('%d/%m')} — {MEALS[key[1]][1]}: {key[2]}")
        await send_message(token, chat, "\n".join(out[:20]), reply_markup=app.kb(RU_KB))
        return

    target = _target_date(text, today)
    rows = await _day_rows(db, uid, target)
    matches = [r for r in rows if keyword in _norm(app.rowget(r, "item_value")) and (not meal or app.rowget(r, "meal_type") == meal)]
    if not matches:
        where = MEALS[meal][1].lower() if meal else "cardápio"
        await send_message(token, chat, f"🍽️ Não achei “{keyword}” no {where} de {target.strftime('%d/%m')}.", reply_markup=app.kb(RU_KB))
        return
    out = [f"✅ Tem “{keyword}” em {target.strftime('%d/%m')}:" ]
    for row in matches[:10]:
        out.append(f"• {MEALS[app.rowget(row, 'meal_type')][1]}: {app.rowget(row, 'item_value')}")
    await send_message(token, chat, "\n".join(out), reply_markup=app.kb(RU_KB))


def _decode(data):
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError("codificação de texto não reconhecida")


def _preview(parsed):
    start, end = date.fromisoformat(parsed["week_start"]), date.fromisoformat(parsed["week_end"])
    out = [f"📥 Prévia do cardápio RU — {start.strftime('%d/%m')} a {end.strftime('%d/%m')}"]
    meals = items = 0
    for day in parsed["days"]:
        d = date.fromisoformat(day["date"])
        names = []
        for meal in ("cafe", "almoco", "jantar"):
            current = day["meals"].get(meal, [])
            if current:
                names.append(MEALS[meal][1])
                meals += 1
                items += len(current)
        out.append(f"• {DAY_NAMES[d.weekday()].capitalize()} {d.strftime('%d/%m')}: {', '.join(names)}")
    out.append(f"\n{len(parsed['days'])} dia(s), {meals} refeição(ões), {items} item(ns).")
    out.append("Responda `confirmar` para salvar/substituir essa semana, ou cancele.")
    return "\n".join(out)


async def handle_message(db, token, message, uid=None, state=None, payload=None):
    chat = (message.get("chat") or {}).get("id")
    if chat is None or not uid:
        return False
    chat = int(chat)
    text = (message.get("text") or "").strip()
    payload = payload or {}
    in_state = state in {"ru_import_wait", "ru_import_confirm"}
    if not in_state and not _looks_ru(text):
        return False
    await _ensure_schema(db)

    if text in {"❌ Cancelar ação", "/cancelar"} and in_state:
        await app.clear_state(db, uid)
        await send_message(token, chat, "Importação do RU cancelada. Nada foi alterado.", reply_markup=app.kb(RU_KB))
        return True

    if state == "ru_import_wait":
        doc = message.get("document")
        if not doc:
            await send_message(token, chat, "Estou esperando um arquivo `.txt`. Foto/PDF precisa ser convertido antes.", reply_markup=app.kb(CANCEL_KB))
            return True
        filename = (doc.get("file_name") or "cardapio.txt").strip()
        mime = (doc.get("mime_type") or "").lower()
        size = int(doc.get("file_size") or 0)
        if size and size > 1_000_000:
            await send_message(token, chat, "Esse TXT passou de 1 MB; envie uma versão menor.", reply_markup=app.kb(CANCEL_KB))
            return True
        if not (filename.lower().endswith(".txt") or mime.startswith("text/")):
            await send_message(token, chat, "Formato aceito aqui: `.txt`. Converta a tabela/foto e envie novamente.", reply_markup=app.kb(CANCEL_KB))
            return True
        try:
            parsed = parse_ru_menu_text(_decode(await get_file_bytes(token, doc["file_id"])))
        except Exception as exc:
            await send_message(token, chat, f"Não consegui ler esse TXT ({type(exc).__name__}). Confira a conversão e tente de novo.", reply_markup=app.kb(CANCEL_KB))
            return True
        if not parsed:
            await send_message(token, chat, "Li o TXT, mas não identifiquei dias + refeições com segurança. Use `[SEGUNDA - 31/08/2026]`, `CAFE`, `ALMOCO`, `JANTAR` e `Categoria: item`.", reply_markup=app.kb(CANCEL_KB))
            return True
        await app.set_state(db, uid, "ru_import_confirm", {"menu": parsed, "filename": filename})
        await send_message(token, chat, _preview(parsed), reply_markup=app.kb(CANCEL_KB))
        return True

    if state == "ru_import_confirm":
        if _norm(text) != "confirmar":
            await send_message(token, chat, "Digite `confirmar` para salvar ou `❌ Cancelar ação`.", reply_markup=app.kb(CANCEL_KB))
            return True
        parsed = payload.get("menu")
        if not parsed:
            await app.clear_state(db, uid)
            await send_message(token, chat, "A prévia expirou. Envie o TXT novamente.", reply_markup=app.kb(RU_KB))
            return True
        inserted = await _save(db, uid, parsed, payload.get("filename") or "cardapio.txt")
        await app.clear_state(db, uid)
        start, end = date.fromisoformat(parsed["week_start"]), date.fromisoformat(parsed["week_end"])
        await send_message(token, chat, f"✅ Cardápio RU salvo: {start.strftime('%d/%m')} a {end.strftime('%d/%m')} ({inserted} item(ns)). Agora pode perguntar `qual o almoço hoje?`.", reply_markup=app.kb(RU_KB))
        return True

    if text in {"🍽️ RU", "🍽️ Restaurante Universitário"}:
        await send_message(token, chat, "🍽️ Restaurante Universitário. Cardápio semanal sem precisar caçar a foto toda vez.", reply_markup=app.kb(RU_KB))
        return True
    if text == "📤 Atualizar cardápio RU" or any(x in _norm(text) for x in ("atualizar cardapio ru", "importar cardapio ru", "novo cardapio do ru")):
        await app.set_state(db, uid, "ru_import_wait", {})
        await send_message(token, chat, "📤 Envie o cardápio semanal em `.txt`.\n\nFormato recomendado:\n`SEMANA: 31/08/2026 a 05/09/2026`\n`[SEGUNDA - 31/08/2026]`\n`ALMOCO`\n`Proteína 01: Frango assado`\n\nEu mostro uma prévia antes de salvar.", reply_markup=app.kb(CANCEL_KB))
        return True
    if text == "🗃️ Cardápios anteriores" or "cardapios anteriores" in _norm(text) or "historico do ru" in _norm(text):
        await _history(db, token, chat, uid)
        return True

    today = app.now_local().date()
    meal = _requested_meal(text)
    keyword = _keyword(text)
    if keyword:
        await _search_food(db, token, chat, uid, text, today, keyword, meal)
        return True
    if text == "📅 Cardápio da semana" or "semana" in _norm(text):
        await _show_week(db, token, chat, uid, today)
        return True
    target = _target_date(text, today)
    if not target:
        await send_message(token, chat, "Não consegui entender a data do cardápio.", reply_markup=app.kb(RU_KB))
        return True
    vegetarian = "vegetariano" in _norm(text) or "vegetariana" in _norm(text)
    await _show_day(db, token, chat, uid, target, meal, vegetarian)
    return True
