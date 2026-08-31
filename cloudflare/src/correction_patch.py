"""Correção segura do item recém-criado/corrigido — Etapa 1.4.

Exemplos:
    marca dentista amanhã às 15h
    não, 16h

    cria uma tarefa entregar relatório sexta às 18h
    quinta não, sexta

    tenho dentista amanhã às 15h
    não é dentista, é oftalmo

    não, 16h
    deixa como tava

O módulo não cria itens e não escolhe alvo por similaridade. Ele só corrige um
``daily_item`` explicitamente marcado no contexto curto como recém-criado,
recém-corrigido ou recém-revertido.
"""

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
    "deixa como tava",
    "deixa como estava",
    "volta como tava",
    "volta como estava",
    "volta pro anterior",
    "volta para o anterior",
    "desfaz",
    "desfaz isso",
    "desfaz a correcao",
    "desfaz essa correcao",
    "esquece essa correcao",
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


def _temporal_tail(text):
    """Prioriza o lado novo de construções como `quinta não, sexta`."""
    raw = (text or "").strip()
    if not raw:
        return raw

    # `quinta não, sexta`, `15h não, 16h`, `amanhã não, terça`.
    replacement = re.match(
        rf"^\s*(?:{_DAY_WORDS}|\d{{1,2}}(?::\d{{2}}|h(?:\d{{1,2}})?)?)\s+"
        r"(?:não|nao)\s*[,;:]?\s*(.+?)\s*$",
        raw,
        flags=re.I,
    )
    if replacement:
        return replacement.group(1).strip()

    # `não, 16h` / `não, sexta`.
    leading = re.match(r"^\s*(?:não|nao)\s*[,;:]\s*(.+?)\s*$", raw, flags=re.I)
    if leading:
        return leading.group(1).strip()
    return raw


def temporal_correction(text, *, today=None):
    """Extrai somente correções explícitas de data/hora, sem efeitos colaterais."""
    if not text or is_undo_phrase(text):
        return None
    if not language.detect_corrections(text):
        # `quinta não, sexta` pode não cair no mesmo marcador de todas as versões
        # do normalizador; a forma explícita abaixo ainda é inequivocamente reparo.
        if not re.search(rf"\b(?:{_DAY_WORDS}|\d{{1,2}}(?::\d{{2}}|h\d{{0,2}})?)\s+(?:não|nao)\b", text, re.I):
            return None

    # `não me lembra...` é uma nova intenção linguística negada, não reparo.
    if language.has_explicit_action(text):
        return None

    candidate = _temporal_tail(text)
    base = today or _now().date()
    due = parse_date(candidate, base)
    tm = parse_time(candidate)
    if due is None and tm is None:
        return None
    return {"date": due, "time": tm}


def title_correction(text):
    """Extrai correção explícita de conteúdo/título quando não há tempo novo."""
    if not text or is_undo_phrase(text):
        return None
    if language.has_explicit_action(text):
        return None
    if temporal_correction(text) is not None:
        return None

    raw = (text or "").strip().rstrip(".!?")

    # `não é dentista, é oftalmo` / `não era dentista, era oftalmo`.
    m = re.match(
        r"^\s*(?:não|nao)\s+(?:é|e|era)\s+(.+?)\s*[,;]\s*(?:é|e|era)\s+(.+?)\s*$",
        raw,
        flags=re.I,
    )
    if m:
        old = m.group(1).strip()
        new = m.group(2).strip()
        return {"expected_old": old, "new_title": new} if old and new else None

    # `dentista não, oftalmo`.
    m = re.match(r"^\s*(.+?)\s+(?:não|nao)\s*[,;:]\s*(.+?)\s*$", raw, flags=re.I)
    if m:
        old = m.group(1).strip()
        new = m.group(2).strip()
        return {"expected_old": old, "new_title": new} if old and new else None

    # `quis dizer oftalmo` / `na verdade é oftalmo`.
    m = re.match(
        r"^\s*(?:quis dizer|corrigindo\s*[:,]?|na verdade(?:\s+(?:é|e|era))?)\s+(.+?)\s*$",
        raw,
        flags=re.I,
    )
    if m:
        new = m.group(1).strip()
        return {"expected_old": None, "new_title": new} if new else None
    return None


def _same_title(expected, current):
    if not expected:
        return True
    a = _norm(expected)
    b = _norm(current)
    return bool(a and b and (a == b or a in b or b in a))


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    return int(_row(row, "id")) if row else None


async def _load_target(db, uid, ctx):
    if not ctx or not ctx.get("id"):
        return None
    detail = ctx.get("detail") or {}
    if detail.get("source") not in ALLOWED_CONTEXT_SOURCES:
        return None
    item_id = int(ctx["id"])
    item = await db.prepare(
        "SELECT id,kind,title,details,due_date,due_time,status FROM daily_items "
        "WHERE id=? AND user_id=?"
    ).bind(item_id, uid).first()
    if not item or _row(item, "status") != "pendente":
        return None
    return item


async def _save_context(db, uid, ctx, item_id, detail):
    logical_kind = ctx.get("kind") or "tarefa"
    await short_context.remember(db, uid, logical_kind, item_id, detail)


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
    current_title = _row(item, "title") or "Item"
    current_date = _row(item, "due_date")
    current_time = _row(item, "due_time")
    detail = ctx.get("detail") or {}

    if undo:
        if detail.get("source") != "corrected" or detail.get("undo_available", True) is False:
            await send_message(
                token,
                chat_id,
                "Não tenho uma correção recente segura para desfazer.",
                reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
            )
            return True

        previous_title = detail.get("previous_title", current_title)
        previous_date = detail.get("previous_date", current_date)
        previous_time = detail.get("previous_time", current_time)
        await db.prepare(
            "UPDATE daily_items SET title=?,due_date=?,due_time=?,status='pendente',snoozed_until=NULL "
            "WHERE id=? AND user_id=?"
        ).bind(previous_title, previous_date, previous_time, item_id, uid).run()
        await _save_context(
            db,
            uid,
            ctx,
            item_id,
            {"source": "reverted", "undo_available": False},
        )
        when = ""
        if previous_date:
            try:
                when = datetime.fromisoformat(previous_date).strftime("%d/%m")
            except Exception:
                when = previous_date
            if previous_time:
                when += f" às {previous_time}"
        suffix = f" — {when}" if when else ""
        await send_message(
            token,
            chat_id,
            f"↩️ Voltei como estava: {previous_title}{suffix}.",
            reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
        )
        return True

    new_title = current_title
    new_date = current_date
    new_time = current_time

    if temporal is not None:
        new_date = temporal["date"].isoformat() if temporal["date"] else current_date
        new_time = temporal["time"] if temporal["time"] else current_time
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
                chat_id,
                msg,
                reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
            )
            return True
    else:
        expected_old = title_change.get("expected_old")
        if not _same_title(expected_old, current_title):
            await send_message(
                token,
                chat_id,
                f"Estou com `{current_title}` como item atual. Essa correção parece apontar para outra coisa, então não alterei nada.",
                reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
            )
            return True
        new_title = title_change["new_title"].strip()[:160]
        if not new_title:
            return False

    await db.prepare(
        "UPDATE daily_items SET title=?,due_date=?,due_time=?,status='pendente',snoozed_until=NULL "
        "WHERE id=? AND user_id=?"
    ).bind(new_title, new_date, new_time, item_id, uid).run()

    await _save_context(
        db,
        uid,
        ctx,
        item_id,
        {
            "source": "corrected",
            "undo_available": True,
            "previous_title": current_title,
            "previous_date": current_date,
            "previous_time": current_time,
        },
    )

    if temporal is not None:
        due_date = datetime.fromisoformat(new_date).date()
        when = due_date.strftime("%d/%m") + (f" às {new_time}" if new_time else "")
        reply = f"✏️ Corrigido: {new_title} — {when}."
    else:
        reply = f"✏️ Corrigido: {current_title} virou {new_title}."

    await send_message(
        token,
        chat_id,
        reply,
        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
    )
    return True
