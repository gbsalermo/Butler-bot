"""Correção temporal segura do item recém-criado — Etapa 1.4.

Exemplos:
    marca dentista amanhã às 15h
    não, 16h

    cria uma tarefa entregar relatório sexta às 18h
    melhor quinta

O módulo não cria itens e não escolhe um alvo por similaridade. Ele só corrige
um ``daily_item`` que tenha sido explicitamente marcado no contexto curto como
``source=created`` ou ``source=corrected``.
"""

from datetime import datetime, timedelta, timezone

import app
import language_primitives as language
import short_context
from nlu import parse_date, parse_time, validate_future
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
ALLOWED_CONTEXT_SOURCES = {"created", "corrected"}


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


def temporal_correction(text, *, today=None):
    """Extrai somente correções explícitas de data/hora, sem efeitos colaterais."""
    if not text or not language.detect_corrections(text):
        return None

    # "não me lembra..." possui marcador superficial de negação, mas é uma nova
    # intenção linguística, não reparo do turno anterior.
    if language.has_explicit_action(text):
        return None

    base = today or _now().date()
    due = parse_date(text, base)
    tm = parse_time(text)
    if due is None and tm is None:
        return None
    return {"date": due, "time": tm}


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    return int(_row(row, "id")) if row else None


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    correction = temporal_correction(text)
    if correction is None:
        return False

    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    uid = await _uid(db, int(chat_id))
    if uid is None:
        return False

    ctx = await short_context.latest(db, uid)
    if not ctx or not ctx.get("id"):
        return False
    detail = ctx.get("detail") or {}
    if detail.get("source") not in ALLOWED_CONTEXT_SOURCES:
        return False

    item_id = int(ctx["id"])
    item = await db.prepare(
        "SELECT id,kind,title,details,due_date,due_time,status FROM daily_items "
        "WHERE id=? AND user_id=?"
    ).bind(item_id, uid).first()
    if not item or _row(item, "status") != "pendente":
        return False

    old_date = _row(item, "due_date")
    old_time = _row(item, "due_time")
    new_date = correction["date"].isoformat() if correction["date"] else old_date
    new_time = correction["time"] if correction["time"] else old_time
    if not new_date:
        return False

    try:
        due_date = datetime.fromisoformat(new_date).date()
    except Exception:
        return False

    ok, msg = validate_future(due_date, new_time, _now().replace(tzinfo=None))
    if not ok:
        await send_message(
            token,
            int(chat_id),
            msg,
            reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
        )
        return True

    await db.prepare(
        "UPDATE daily_items SET due_date=?,due_time=?,status='pendente',snoozed_until=NULL "
        "WHERE id=? AND user_id=?"
    ).bind(new_date, new_time, item_id, uid).run()

    logical_kind = ctx.get("kind") or _row(item, "kind")
    await short_context.remember(
        db,
        uid,
        logical_kind,
        item_id,
        {
            "source": "corrected",
            "previous_date": old_date,
            "previous_time": old_time,
        },
    )

    when = due_date.strftime("%d/%m") + (f" às {new_time}" if new_time else "")
    await send_message(
        token,
        int(chat_id),
        f"✏️ Corrigido: {_row(item, 'title')} — {when}.",
        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
    )
    return True
