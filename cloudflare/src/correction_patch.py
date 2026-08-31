"""Auto-reparo conversacional seguro do item recém-criado/corrigido — Etapa 1.4."""

import re
from datetime import datetime, timedelta, timezone

import app
import language_primitives as language
import short_context
from nlu import parse_date, parse_time, validate_future
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
ALLOWED_CONTEXT_SOURCES = {"created", "corrected", "reverted"}
UNDO_PHRASES = {
    "deixa como tava", "deixa como estava", "volta como tava", "volta como estava",
    "volta pro anterior", "volta para o anterior", "desfaz", "desfaz isso",
    "desfaz a correcao", "desfaz essa correcao", "esquece essa correcao",
}
_DAY_WORDS = "segunda|terca|terça|quarta|quinta|sexta|sabado|sábado|domingo|hoje|amanha|amanhã"


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


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


def _norm(text):
    return language.normalize_text(language.strip_butler(text))


def is_undo_phrase(text):
    return _norm(text) in UNDO_PHRASES


def _explicit_title_pair(text):
    """Retorna X→Y em formas inequivocamente reparativas, antes da NLU geral."""
    raw = (text or "").strip().rstrip(".!?")
    m = re.match(
        r"^\s*(?:não|nao)\s+(?:é|e|era)\s+(.+?)\s*[,;]\s*(?:é|e|era)\s+(.+?)\s*$",
        raw, flags=re.I,
    )
    if not m:
        m = re.match(r"^\s*(.+?)\s+(?:não|nao)\s*[,;:]\s*(.+?)\s*$", raw, flags=re.I)
    if not m:
        return None
    old, new = m.group(1).strip(), m.group(2).strip()
    return {"expected_old": old, "new_title": new} if old and new else None


def _temporal_tail(text):
    raw = (text or "").strip()
    replacement = re.match(
        rf"^\s*(?:{_DAY_WORDS}|\d{{1,2}}(?::\d{{2}}|h(?:\d{{1,2}})?)?)\s+"
        r"(?:não|nao)\s*[,;:]?\s*(.+?)\s*$",
        raw, flags=re.I,
    )
    if replacement:
        return replacement.group(1).strip()
    leading = re.match(r"^\s*(?:não|nao)\s*[,;:]\s*(.+?)\s*$", raw, flags=re.I)
    return leading.group(1).strip() if leading else raw


def temporal_correction(text, *, today=None):
    if not text or is_undo_phrase(text):
        return None
    if not language.detect_corrections(text):
        if not re.search(
            rf"\b(?:{_DAY_WORDS}|\d{{1,2}}(?::\d{{2}}|h\d{{0,2}})?)\s+(?:não|nao)\b",
            text, re.I,
        ):
            return None
    if language.has_explicit_action(text):
        return None

    candidate = _temporal_tail(text)
    base = today or _now().date()
    due, tm = parse_date(candidate, base), parse_time(candidate)
    return None if due is None and tm is None else {"date": due, "time": tm}


def title_correction(text):
    if not text or is_undo_phrase(text):
        return None

    # `dentista não, oftalmo` precisa vencer a classificação superficial de
    # `dentista` como compromisso. O alvo antigo será validado contra o contexto.
    pair = _explicit_title_pair(text)
    if pair:
        return pair

    if language.has_explicit_action(text) or temporal_correction(text) is not None:
        return None

    raw = (text or "").strip().rstrip(".!?")
    m = re.match(
        r"^\s*(?:quis dizer|corrigindo\s*[:,]?|na verdade(?:\s+(?:é|e|era))?)\s+(.+?)\s*$",
        raw, flags=re.I,
    )
    if not m:
        return None
    new = m.group(1).strip()
    return {"expected_old": None, "new_title": new} if new else None


def _same_title(expected, current):
    if not expected:
        return True
    a, b = _norm(expected), _norm(current)
    return bool(a and b and (a == b or a in b or b in a))


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    return int(_row(row, "id")) if row else None


async def _load_target(db, uid, ctx):
    if not ctx or not ctx.get("id"):
        return None
    if (ctx.get("detail") or {}).get("source") not in ALLOWED_CONTEXT_SOURCES:
        return None
    item = await db.prepare(
        "SELECT id,kind,title,details,due_date,due_time,status FROM daily_items WHERE id=? AND user_id=?"
    ).bind(int(ctx["id"]), uid).first()
    return item if item and _row(item, "status") == "pendente" else None


async def _remember(db, uid, ctx, item_id, detail):
    await short_context.remember(db, uid, ctx.get("kind") or "tarefa", item_id, detail)


def _when(date_value, time_value):
    if not date_value:
        return ""
    try:
        label = datetime.fromisoformat(date_value).strftime("%d/%m")
    except Exception:
        label = str(date_value)
    return label + (f" às {time_value}" if time_value else "")


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    undo = is_undo_phrase(text)
    temporal = None if undo else temporal_correction(text)
    title_change = None if undo or temporal is not None else title_correction(text)
    if not undo and temporal is None and title_change is None:
        return False

    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    chat_id = int(chat_id)
    uid = await _uid(db, chat_id)
    if uid is None:
        return False

    ctx = await short_context.latest(db, uid)
    item = await _load_target(db, uid, ctx)
    if item is None:
        return False

    item_id = int(_row(item, "id"))
    old_title = _row(item, "title") or "Item"
    old_date = _row(item, "due_date")
    old_time = _row(item, "due_time")
    detail = ctx.get("detail") or {}

    if undo:
        if detail.get("source") != "corrected" or detail.get("undo_available", True) is False:
            await send_message(token, chat_id, "Não tenho uma correção recente segura para desfazer.",
                               reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True})
            return True
        title = detail.get("previous_title", old_title)
        due_date = detail.get("previous_date", old_date)
        due_time = detail.get("previous_time", old_time)
        await db.prepare(
            "UPDATE daily_items SET title=?,due_date=?,due_time=?,status='pendente',snoozed_until=NULL WHERE id=? AND user_id=?"
        ).bind(title, due_date, due_time, item_id, uid).run()
        await _remember(db, uid, ctx, item_id, {"source": "reverted", "undo_available": False})
        suffix = f" — {_when(due_date, due_time)}" if due_date else ""
        await send_message(token, chat_id, f"↩️ Voltei como estava: {title}{suffix}.",
                           reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True})
        return True

    new_title, new_date, new_time = old_title, old_date, old_time
    if temporal is not None:
        new_date = temporal["date"].isoformat() if temporal["date"] else old_date
        new_time = temporal["time"] if temporal["time"] else old_time
        if not new_date:
            return False
        try:
            parsed_date = datetime.fromisoformat(new_date).date()
        except Exception:
            return False
        ok, msg = validate_future(parsed_date, new_time, _now().replace(tzinfo=None))
        if not ok:
            await send_message(token, chat_id, msg,
                               reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True})
            return True
    else:
        if not _same_title(title_change.get("expected_old"), old_title):
            await send_message(
                token, chat_id,
                f"Estou com `{old_title}` como item atual. Essa correção parece apontar para outra coisa, então não alterei nada.",
                reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
            )
            return True
        new_title = title_change["new_title"].strip()[:160]
        if not new_title:
            return False

    await db.prepare(
        "UPDATE daily_items SET title=?,due_date=?,due_time=?,status='pendente',snoozed_until=NULL WHERE id=? AND user_id=?"
    ).bind(new_title, new_date, new_time, item_id, uid).run()
    await _remember(db, uid, ctx, item_id, {
        "source": "corrected", "undo_available": True,
        "previous_title": old_title, "previous_date": old_date, "previous_time": old_time,
    })

    reply = (
        f"✏️ Corrigido: {new_title} — {_when(new_date, new_time)}."
        if temporal is not None
        else f"✏️ Corrigido: {old_title} virou {new_title}."
    )
    await send_message(token, chat_id, reply,
                       reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True})
    return True
