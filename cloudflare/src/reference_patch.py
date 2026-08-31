import json
import re
from datetime import datetime, timedelta, timezone

import app
import conversation_layer
import language_primitives as language
import short_context
from nlu import parse_date, parse_time
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))


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


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


async def _uid(db, chat):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat).first()
    return int(_row(row, "id")) if row else None


async def _recent_distinct_targets(db, uid, limit=6):
    rows = await _rows(
        db.prepare(
            "SELECT target_id,detail,created_at FROM natural_events "
            "WHERE user_id=? AND event_type='context' AND target_id IS NOT NULL "
            "ORDER BY id DESC LIMIT 12"
        ).bind(uid)
    )
    out = []
    for row in rows:
        if not short_context.context_is_fresh(_row(row, "created_at")):
            continue
        try:
            target_id = int(_row(row, "target_id"))
        except Exception:
            continue
        if target_id not in out:
            out.append(target_id)
        if len(out) >= limit:
            break
    return out


async def _resolve_previous(db, uid, text, ctx):
    values = {ref.get("value") for ref in language.detect_references(text)}
    if values.intersection({"a ultima", "o ultimo"}):
        try:
            return int(ctx.get("id"))
        except Exception:
            return None
    if not values.intersection({"a anterior", "o anterior"}):
        return None
    history = await _recent_distinct_targets(db, uid)
    return history[1] if len(history) > 1 else None


async def _alternative_candidates(db, uid, ctx):
    ids = []
    for value in ctx.get("candidate_ids") or []:
        try:
            ids.append(int(value))
        except Exception:
            pass
    current = ctx.get("id")
    alternatives = [item_id for item_id in ids if item_id != current]
    if alternatives:
        return alternatives

    if not current or ctx.get("kind") not in ("tarefa", "compromisso", "lembrete"):
        return []
    rows = await _rows(
        db.prepare(
            "SELECT id FROM daily_items WHERE user_id=? AND status='pendente' AND id!=? AND kind=? "
            "ORDER BY due_date,due_time,id DESC LIMIT 5"
        ).bind(uid, int(current), ctx.get("kind"))
    )
    return [int(_row(row, "id")) for row in rows]


def _action_family(text):
    families = set(language.detect_action_families(text))
    for family in ("complete", "cancel", "reschedule"):
        if family in families:
            return family
    normalized = language.normalize_text(language.strip_butler(text))
    if normalized.startswith(("mantem ", "mantenha ")) or normalized in {"mantem", "pendente"}:
        return "keep"
    return None


async def _delegate_context_action(db, token, message, uid, item_id, family):
    original = (message.get("text") or "").strip()
    synthetic = dict(message)
    if family == "complete":
        synthetic["text"] = f"conclui #{item_id}"
    elif family == "cancel":
        synthetic["text"] = f"cancela #{item_id}"
    elif family == "reschedule":
        # `conversation_layer` já é autoridade de adiar/mover daily_items.
        # Prefixamos `passa` apenas para garantir que conjugações como `muda`
        # entrem no fluxo autoritativo, preservando data/hora do texto original.
        synthetic["text"] = f"passa #{item_id} {original}"
    elif family == "keep":
        synthetic["text"] = f"mantem #{item_id} pendente"
    else:
        return False

    handled = await conversation_layer.handle_message(db, token, synthetic)
    if handled:
        row = await db.prepare("SELECT kind FROM daily_items WHERE id=? AND user_id=?").bind(item_id, uid).first()
        if row:
            await short_context.remember(db, uid, _row(row, "kind"), item_id)
    return handled


async def handle_reference(db, token, message):
    chat = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat:
        return False
    uid = await _uid(db, int(chat))
    if not uid:
        return False

    refs = language.detect_references(text)
    family = _action_family(text)

    # Ações com referência natural são resolvidas aqui e delegadas ao domínio.
    if refs and family:
        ctx = await short_context.latest(db, uid)
        if not ctx:
            await send_message(
                token,
                int(chat),
                "Perdi o contexto dessa referência. Me diga o nome da tarefa/compromisso ou abra a lista de novo.",
                reply_markup=_kb(app.MAIN_KB),
            )
            return True

        values = {ref.get("value") for ref in refs}
        target_id = await _resolve_previous(db, uid, text, ctx)

        if target_id is None and values.intersection({"a outra", "o outro"}):
            alternatives = await _alternative_candidates(db, uid, ctx)
            if len(alternatives) == 1:
                target_id = alternatives[0]
            elif alternatives:
                rows = []
                for item_id in alternatives:
                    row = await db.prepare(
                        "SELECT id,title FROM daily_items WHERE id=? AND user_id=?"
                    ).bind(item_id, uid).first()
                    if row:
                        rows.append(row)
                await send_message(
                    token,
                    int(chat),
                    "Tenho mais de uma opção para 'a outra'. Escolha pelo número:\n"
                    + "\n".join(f"• #{_row(row,'id')} {_row(row,'title')}" for row in rows),
                    reply_markup=_kb(app.MAIN_KB),
                )
                return True

        if target_id is None:
            resolved = await short_context.resolve_daily_item(db, uid, text)
            if resolved:
                target_id = int(_row(resolved, "id"))

        if target_id is None:
            await send_message(
                token,
                int(chat),
                "Não consegui identificar com segurança qual item você quis dizer. Use o nome ou abra a lista e diga `a primeira`, `a segunda` etc.",
                reply_markup=_kb(app.MAIN_KB),
            )
            return True

        if await _delegate_context_action(db, token, message, uid, target_id, family):
            return True

    normalized = language.normalize_text(language.strip_butler(text))
    ctx = await short_context.latest(db, uid)
    ctx_id = ctx.get("id") if ctx else None

    # `essa não, a outra` sem ação apenas troca o foco conversacional.
    if refs and values_intersection(refs, {"a outra", "o outro"}) and ctx_id:
        alternatives = await _alternative_candidates(db, uid, ctx)
        if len(alternatives) == 1:
            item_id = alternatives[0]
            row = await db.prepare("SELECT id,kind,title FROM daily_items WHERE id=? AND user_id=?").bind(item_id, uid).first()
            if row:
                await short_context.remember(db, uid, _row(row, "kind"), item_id)
                await send_message(token, int(chat), f"Certo, então estamos falando de #{item_id} {_row(row,'title')}. Continue.", reply_markup=_kb(app.MAIN_KB))
                return True
        elif alternatives:
            rows = []
            for item_id in alternatives:
                row = await db.prepare("SELECT id,title FROM daily_items WHERE id=? AND user_id=?").bind(item_id, uid).first()
                if row:
                    rows.append(row)
            await send_message(token, int(chat), "Tenho mais de uma 'outra'. Escolha pelo número:\n" + "\n".join(f"• #{_row(row,'id')} {_row(row,'title')}" for row in rows), reply_markup=_kb(app.MAIN_KB))
            return True

    if "proxima semana" in normalized and any(x in normalized for x in ("passa", "joga", "adia", "adiar")) and ctx_id:
        row = await db.prepare("SELECT id,kind,title,due_date,due_time FROM daily_items WHERE id=? AND user_id=?").bind(ctx_id, uid).first()
        if row:
            try:
                base = datetime.fromisoformat(_row(row, "due_date")).date() if _row(row, "due_date") else _now().date()
            except Exception:
                base = _now().date()
            target_date = base + timedelta(days=7)
            await db.prepare("UPDATE daily_items SET due_date=?,status='pendente',postpone_count=postpone_count+1 WHERE id=? AND user_id=?").bind(target_date.isoformat(), ctx_id, uid).run()
            await short_context.remember(db, uid, _row(row, "kind"), int(_row(row, "id")))
            await send_message(token, int(chat), f"⏰ {_row(row,'title')} foi para {target_date.strftime('%d/%m')}" + (f" às {_row(row,'due_time')}" if _row(row, "due_time") else "") + ". Semana que vem ganhou mais um problema. 😌", reply_markup=_kb(app.MAIN_KB))
            return True

    # Cancelamento por data/hora continua disponível quando não há pronome.
    if "cancela" in normalized or "cancelar" in normalized:
        target_date = parse_date(text, _now().date())
        target_time = parse_time(text)
        if target_date and target_time and any(x in normalized for x in ("o que marquei", "o compromisso", "a tarefa", "o que eu marquei")):
            rows = await _rows(db.prepare("SELECT id,kind,title FROM daily_items WHERE user_id=? AND status='pendente' AND due_date=? AND due_time=?").bind(uid, target_date.isoformat(), target_time))
            if len(rows) == 1:
                row = rows[0]
                await db.prepare("UPDATE daily_items SET status='cancelado',cancelled_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?").bind(_row(row, "id"), uid).run()
                await short_context.remember(db, uid, _row(row, "kind"), int(_row(row, "id")))
                await send_message(token, int(chat), f"🚫 {_row(row,'title')} cancelado. Era o item de {target_date.strftime('%d/%m')} às {target_time}.", reply_markup=_kb(app.MAIN_KB))
                return True
            if len(rows) > 1:
                await send_message(token, int(chat), "Tem mais de uma coisa nesse horário. Escolha pelo #ID:\n" + "\n".join(f"• #{_row(row,'id')} {_row(row,'title')}" for row in rows), reply_markup=_kb(app.MAIN_KB))
                return True
    return False


def values_intersection(refs, values):
    return bool({ref.get("value") for ref in refs}.intersection(values))
