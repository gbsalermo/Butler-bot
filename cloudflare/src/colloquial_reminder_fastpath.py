"""Lembretes coloquiais explícitos sem reativar NLU ampla.

Aceita criação completa em uma frase e continua de forma guiada quando faltar
data ou horário. Um lembrete nunca é descartado só porque o usuário omitiu uma
parte temporal.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

import app
from nlu import parse_date, parse_time, validate_future
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
STATE_DATE = "fast_reminder_date"
STATE_TIME = "fast_reminder_time"


def _norm(text):
    v = unicodedata.normalize("NFKD", (text or "").lower())
    v = "".join(c for c in v if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", v).strip()


def _row(row, key, default=None):
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    return int(_row(row, "id")) if row else None


def _looks_like_request(n):
    patterns = (
        r"^(?:butler[, ]+)?(?:me\s+)?(?:lembra|lembre|avisa|avise)\b",
        r"^(?:butler[, ]+)?(?:cria|crie|faz|faca|anota|coloca|adiciona)\s+(?:um\s+|uma\s+)?lembrete\b",
        r"^(?:butler[, ]+)?(?:nao|não)\s+deixa\s+(?:eu\s+)?esquecer\b",
        r"^(?:butler[, ]+)?(?:me\s+)?da\s+(?:um\s+)?toque\b",
        r"^(?:butler[, ]+)?(?:me\s+)?chama\s+(?:a\s+)?atencao\b",
        r"^(?:butler[, ]+)?(?:so\s+)?(?:me\s+)?recorda\b",
        r"^(?:butler[, ]+)?lembra\s+eu\b",
    )
    return any(re.search(p, n) for p in patterns)


def _clean_title(text):
    value = text.strip()
    prefixes = (
        r"^(?:Butler[,!:\-]?\s*)?(?:me\s+)?(?:lembra|lembre|avisa|avise)(?:-me)?\s*(?:de\s+|que\s+)?",
        r"^(?:Butler[,!:\-]?\s*)?(?:cria|crie|faz|faça|faca|anota|coloca|adiciona)\s+(?:um\s+|uma\s+)?lembrete\s*(?:de\s+|para\s+|pra\s+)?",
        r"^(?:Butler[,!:\-]?\s*)?(?:não|nao)\s+deixa\s+(?:eu\s+)?esquecer\s*(?:de\s+|que\s+)?",
        r"^(?:Butler[,!:\-]?\s*)?(?:me\s+)?dá\s+(?:um\s+)?toque\s*(?:pra|para|de|que)?\s*",
        r"^(?:Butler[,!:\-]?\s*)?(?:me\s+)?da\s+(?:um\s+)?toque\s*(?:pra|para|de|que)?\s*",
        r"^(?:Butler[,!:\-]?\s*)?(?:só\s+)?(?:me\s+)?recorda\s*(?:de\s+|que\s+)?",
    )
    for p in prefixes:
        new = re.sub(p, "", value, flags=re.I)
        if new != value:
            value = new
            break
    value = re.sub(r"\b(?:hoje|amanhã|amanha)\b", "", value, flags=re.I)
    value = re.sub(r"\b(?:segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)(?:-feira)?\b", "", value, flags=re.I)
    value = re.sub(r"\b(?:dia\s+)?\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", "", value, flags=re.I)
    value = re.sub(r"(?:às|as)\s*\d{1,2}(?::\d{2}|h\d{0,2})?", "", value, flags=re.I)
    value = re.sub(r"\b\d{1,2}(?::\d{2}|h\d{0,2})\b", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip(" ,.-") or "lembrete"


async def _save(db, token, chat_id, uid, title, due, tm):
    ok, msg = validate_future(due, tm, _now().replace(tzinfo=None))
    if not ok:
        await app.clear_state(db, uid)
        await send_message(token, int(chat_id), msg)
        return True

    row = await db.prepare(
        "INSERT INTO daily_items(user_id,kind,title,details,due_date,due_time,status) "
        "VALUES(?,'tarefa',?,'simple_reminder',?,?,'pendente') RETURNING id"
    ).bind(uid, title, due.isoformat(), tm).first()
    iid = int(_row(row, "id"))
    await app.clear_state(db, uid)

    try:
        import conversation_layer
        await conversation_layer._remember(db, uid, "lembrete", iid)
    except Exception:
        pass

    await send_message(
        token,
        int(chat_id),
        f"🔔 Fechado. Te lembro em {due.strftime('%d/%m')} às {tm}: {title}.",
        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
    )
    return True


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if chat_id is None or not text:
        return False

    uid = await _uid(db, int(chat_id))
    if uid is None:
        return False

    # Continuação de um lembrete iniciado anteriormente.
    state, payload = await app.get_state(db, uid)
    if state in (STATE_DATE, STATE_TIME):
        n = _norm(text)
        if n in ("cancelar", "cancelar acao", "❌ cancelar ação", "/cancelar"):
            await app.clear_state(db, uid)
            return False

        title = (payload or {}).get("title") or "lembrete"
        if state == STATE_DATE:
            due = parse_date(text, _now().date())
            if not due:
                await send_message(token, int(chat_id), "📅 Qual dia? Pode mandar `amanhã`, `sexta` ou `24/09`.")
                return True
            tm = (payload or {}).get("time") or parse_time(text)
            if tm:
                return await _save(db, token, chat_id, uid, title, due, tm)
            await app.set_state(db, uid, STATE_TIME, {"title": title, "due_date": due.isoformat()})
            await send_message(token, int(chat_id), f"⏰ Certo, {due.strftime('%d/%m')}. Que horas? Ex.: `15h` ou `15:30`.")
            return True

        tm = parse_time(text)
        if not tm:
            await send_message(token, int(chat_id), "⏰ Qual horário? Ex.: `15h` ou `15:30`.")
            return True
        try:
            due = date.fromisoformat((payload or {}).get("due_date"))
        except Exception:
            await app.clear_state(db, uid)
            return False
        return await _save(db, token, chat_id, uid, title, due, tm)

    n = _norm(text)
    if not _looks_like_request(n):
        return False

    title = _clean_title(text)
    due = parse_date(text, _now().date())
    tm = parse_time(text)

    if due and tm:
        return await _save(db, token, chat_id, uid, title, due, tm)

    if due:
        await app.set_state(db, uid, STATE_TIME, {"title": title, "due_date": due.isoformat()})
        await send_message(
            token,
            int(chat_id),
            f"🔔 Entendi: {title} — {due.strftime('%d/%m')}. Que horas quer que eu te lembre? Ex.: `15h` ou `15:30`.",
            reply_markup={"keyboard": [["❌ Cancelar ação"]], "resize_keyboard": True},
        )
        return True

    if tm:
        await app.set_state(db, uid, STATE_DATE, {"title": title, "time": tm})
        await send_message(
            token,
            int(chat_id),
            f"🔔 Entendi: {title} às {tm}. Em qual dia? Pode mandar `hoje`, `amanhã`, `sexta` ou `24/09`.",
            reply_markup={"keyboard": [["❌ Cancelar ação"]], "resize_keyboard": True},
        )
        return True

    await app.set_state(db, uid, STATE_DATE, {"title": title})
    await send_message(
        token,
        int(chat_id),
        f"🔔 Entendi: {title}. Em qual dia? Pode mandar `hoje`, `amanhã`, `sexta` ou `24/09`.",
        reply_markup={"keyboard": [["❌ Cancelar ação"]], "resize_keyboard": True},
    )
    return True
