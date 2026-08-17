"""Lembretes coloquiais explícitos sem reativar NLU ampla."""

import re
import unicodedata
from datetime import datetime, timedelta, timezone

import app
from nlu import parse_date, parse_time, validate_future
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))


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


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if chat_id is None or not text:
        return False
    n = _norm(text)

    patterns = (
        r"^(?:butler[, ]+)?(?:nao|não)\s+deixa\s+(?:eu\s+)?esquecer\b",
        r"^(?:butler[, ]+)?(?:me\s+)?da\s+(?:um\s+)?toque\b",
        r"^(?:butler[, ]+)?(?:me\s+)?chama\s+(?:a\s+)?atencao\b",
        r"^(?:butler[, ]+)?(?:so\s+)?(?:me\s+)?recorda\b",
        r"^(?:butler[, ]+)?lembra\s+eu\b",
    )
    if not any(re.search(p, n) for p in patterns):
        return False

    due = parse_date(text, _now().date())
    tm = parse_time(text)
    if not due or not tm:
        return False
    ok, msg = validate_future(due, tm, _now().replace(tzinfo=None))
    if not ok:
        await send_message(token, int(chat_id), msg)
        return True

    uid_row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    if not uid_row:
        return False
    uid = int(_row(uid_row, "id"))

    title = text
    title = re.sub(r"^(?:Butler[,!:\-]?\s*)?(?:não|nao)\s+deixa\s+(?:eu\s+)?esquecer\s*(?:de\s+|que\s+)?", "", title, flags=re.I)
    title = re.sub(r"^(?:Butler[,!:\-]?\s*)?(?:me\s+)?dá\s+(?:um\s+)?toque\s*(?:pra|para|de|que)?\s*", "", title, flags=re.I)
    title = re.sub(r"^(?:Butler[,!:\-]?\s*)?(?:me\s+)?da\s+(?:um\s+)?toque\s*(?:pra|para|de|que)?\s*", "", title, flags=re.I)
    title = re.sub(r"^(?:Butler[,!:\-]?\s*)?(?:só\s+)?(?:me\s+)?recorda\s*(?:de\s+|que\s+)?", "", title, flags=re.I)
    title = re.sub(r"\b(?:hoje|amanhã|amanha)\b", "", title, flags=re.I)
    title = re.sub(r"(?:às|as)\s*\d{1,2}(?::\d{2}|h\d{0,2})?", "", title, flags=re.I).strip(" ,.-")

    row = await db.prepare(
        "INSERT INTO daily_items(user_id,kind,title,details,due_date,due_time,status) VALUES(?,'tarefa',?,'simple_reminder',?,?,'pendente') RETURNING id"
    ).bind(uid, title or "lembrete", due.isoformat(), tm).first()
    iid = int(_row(row, "id"))

    try:
        import conversation_layer
        await conversation_layer._remember(db, uid, "lembrete", iid)
    except Exception:
        pass

    await send_message(
        token,
        int(chat_id),
        f"🔔 Pode deixar. Te dou um toque em {due.strftime('%d/%m')} às {tm}: {title or 'lembrete'}.",
        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
    )
    return True
