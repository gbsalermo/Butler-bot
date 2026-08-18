import re
import unicodedata
from datetime import datetime, timedelta, timezone

import app
import routine_integration
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _row(row, key, default=None):
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


async def _notified(db, uid, key):
    row = await db.prepare(
        "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
    ).bind(uid, key).first()
    return bool(row)


def _class_bounds(now, start, end):
    sh, sm = map(int, start.split(":"))
    target = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    try:
        eh, em = map(int, (end or "").split(":"))
        end_target = now.replace(hour=eh, minute=em, second=0, microsecond=0)
        if end_target <= target:
            end_target += timedelta(days=1)
    except Exception:
        end_target = target + timedelta(minutes=60)
    return target, end_target


async def _attendance_tick_exists(db, when):
    try:
        row = await db.prepare(
            "SELECT id FROM attendance_scheduler_ticks WHERE ran_at_local=? LIMIT 1"
        ).bind(when.strftime("%Y-%m-%d %H:%M")).first()
        return bool(row)
    except Exception:
        return None


async def _attendance_last_tick(db):
    try:
        return await db.prepare(
            "SELECT ran_at_local,session_count FROM attendance_scheduler_ticks ORDER BY id DESC LIMIT 1"
        ).first()
    except Exception:
        return None


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    n = _norm(text)
    if n not in {"diagnostico alertas", "diagnostico de alertas", "status alertas", "verificar alertas"}:
        return False

    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    chat_id = int(chat_id)
    uid = await _uid(db, chat_id)
    if uid is None:
        return False

    now = datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    today = now.date()
    out = [f"🧪 Diagnóstico de alertas — {today.strftime('%d/%m')} {now.strftime('%H:%M')}"]

    assistant = await db.prepare(
        "SELECT COALESCE(day_off,0) day_off FROM assistant_state WHERE user_id=?"
    ).bind(uid).first()
    out.append(f"Day-off: {'sim' if int(_row(assistant,'day_off',0) or 0) else 'não'}")

    items = await _rows(db.prepare(
        "SELECT id,kind,title,details,due_time,status FROM daily_items "
        "WHERE user_id=? AND due_date=? AND due_time IS NOT NULL ORDER BY due_time"
    ).bind(uid, today.isoformat()))
    out.append("\n📋 Itens do dia")
    if not items:
        out.append("• nenhum com horário")
    for item in items:
        iid = int(_row(item, "id"))
        kind = _row(item, "kind")
        details = _row(item, "details") or ""
        due = _row(item, "due_time")
        if details.startswith("exam:"):
            continue
        simple = details == "simple_reminder"
        advance = 5 if (kind == "compromisso" and not simple) else 0
        try:
            h, m = map(int, due.split(":"))
            desired = now.replace(hour=h, minute=m, second=0, microsecond=0) - timedelta(minutes=advance)
        except Exception:
            continue
        key = f"item:new:{iid}:{today}:{desired.strftime('%H:%M')}"
        sent = await _notified(db, uid, key)
        label = "lembrete" if simple else kind
        state = (
            "🔔 notificado" if sent else
            "✅ concluído" if _row(item, "status") == "concluido" else
            "⏳ pendente" if now < desired else
            "🚨 vencido sem notificação"
        )
        out.append(f"• {due} {label}: {_row(item,'title')} — {state}")

    routines = await _rows(db.prepare(
        "SELECT id,name,time_hhmm,weekdays FROM routines "
        "WHERE user_id=? AND active=1 AND time_hhmm IS NOT NULL ORDER BY name"
    ).bind(uid))
    out.append("\n🧘 Rotinas")
    if not routines:
        out.append("• nenhuma ativa com horário")
    for routine in routines:
        if not routine_integration._applies(_row(routine, "weekdays"), today):
            continue
        rid = int(_row(routine, "id"))
        scheduled = routine_integration._times(_row(routine, "time_hhmm"))
        done = await routine_integration._status(db, rid, today, scheduled)
        out.append(f"• {_row(routine,'name')}")
        for target in scheduled:
            key = f"routine:{rid}:{today.isoformat()}:{target}"
            sent = await _notified(db, uid, key)
            if target in done:
                state = "✅ feito"
            elif sent:
                state = "🔔 notificado"
            else:
                try:
                    h, m = map(int, target.split(":"))
                    desired = now.replace(hour=h, minute=m, second=0, microsecond=0)
                    state = "⏳ pendente" if now < desired else "🚨 vencido sem notificação"
                except Exception:
                    state = "⚠️ horário inválido"
            out.append(f"  {target} — {state}")

    weekday = app.WEEKDAY_NAMES[now.weekday()]
    sessions = await _rows(db.prepare(
        "SELECT ss.id,ss.start_time,ss.end_time,s.name FROM subject_sessions ss "
        "JOIN subjects s ON s.id=ss.subject_id "
        "WHERE s.user_id=? AND s.active=1 AND ss.weekday=? ORDER BY ss.start_time"
    ).bind(uid, weekday))
    out.append("\n🎓 Aulas")

    last_tick = await _attendance_last_tick(db)
    if last_tick:
        out.append(
            f"Scheduler acadêmico: último tick {_row(last_tick,'ran_at_local')} "
            f"({_row(last_tick,'session_count',0)} sessões do dia)"
        )
    else:
        out.append("Scheduler acadêmico: ⚠️ sem heartbeat disponível nesta versão/execução")

    if not sessions:
        out.append("• nenhuma hoje")

    for session in sessions:
        sid = int(_row(session, "id"))
        start = _row(session, "start_time")
        end = _row(session, "end_time")
        try:
            target, end_target = _class_bounds(now, start, end)
            pre_target = target - timedelta(minutes=10)

            pre_key = f"attendance:pre:{today.isoformat()}:{sid}"
            start_key = f"attendance:start:{today.isoformat()}:{sid}"
            legacy_key = f"attendance:{today.isoformat()}:{sid}"
            pre_sent = await _notified(db, uid, pre_key)
            start_sent = await _notified(db, uid, start_key) or await _notified(db, uid, legacy_key)

            pre_tick = await _attendance_tick_exists(db, pre_target)
            start_tick = await _attendance_tick_exists(db, target)

            if pre_sent:
                pre_state = "🔔 10 min enviado"
            elif now < pre_target:
                pre_state = "⏳ pré-aviso ainda não chegou"
            elif now < target:
                pre_state = "🚨 pré-aviso deveria disparar"
            else:
                pre_state = "⚠️ pré-aviso não foi registrado"

            if start_sent:
                start_state = "🔔 início enviado"
            elif now < target:
                start_state = "⏳ início ainda não chegou"
            elif now < end_target:
                start_state = "🚨 aula em andamento sem aviso inicial — deve recuperar"
            else:
                start_state = "⚠️ aula terminou sem aviso inicial"

            tick_parts = []
            if pre_tick is not None and now >= pre_target:
                tick_parts.append(f"T-10={'✅ tick' if pre_tick else '❌ sem tick'}")
            if start_tick is not None and now >= target:
                tick_parts.append(f"T0={'✅ tick' if start_tick else '❌ sem tick'}")
            tick_note = f" | {'; '.join(tick_parts)}" if tick_parts else ""

            out.append(
                f"• {start}–{end} {_row(session,'name')}\n"
                f"  {pre_state}\n"
                f"  {start_state}{tick_note}"
            )
        except Exception:
            out.append(f"• {start}–{end} {_row(session,'name')} — ⚠️ horário inválido")

    out.append(
        "\nLegenda: `❌ sem tick` significa que o bloco acadêmico não executou naquele minuto; "
        "`✅ tick` sem notificação aponta falha dentro do envio/processamento do Butler."
    )
    await send_message(token, chat_id, "\n".join(out))
    return True
