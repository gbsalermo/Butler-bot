"""Resumos matutino/semanal com recuperação e confirmação real de entrega."""

from datetime import datetime, timedelta, timezone

import app
from settings import (
    UTC_OFFSET_HOURS,
    MORNING_SUMMARY_HOUR,
    MORNING_SUMMARY_MINUTE,
    WEEKLY_SUMMARY_WEEKDAY,
    WEEKLY_SUMMARY_HOUR,
    WEEKLY_SUMMARY_MINUTE,
)
from telegram_api import delivery_error, delivery_ok, send_message
from weather_service import fetch_daily_forecast, get_location
from weather_personality import forecast_comment

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
MORNING_RECOVERY_MINUTES = 300
WEEKLY_GRACE_MINUTES = 60


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


def _within_window(now, hour, minute, grace_minutes):
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    delta = (now - target).total_seconds() / 60
    return 0 <= delta <= grace_minutes


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _checked_send(token, chat, text):
    result = await send_message(token, chat, text, reply_markup=_kb(app.MAIN_KB))
    if not delivery_ok(result):
        raise RuntimeError(f"Telegram não confirmou resumo: {delivery_error(result)}")
    return result


async def _already_sent(db, uid, key):
    existing = await db.prepare(
        "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
    ).bind(uid, key).first()
    return bool(existing)


def _join_names(names):
    names = [str(name).strip() for name in names if str(name).strip()]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} e {names[1]}"
    return ", ".join(names[:-1]) + f" e {names[-1]}"


async def _brief_weather(db, uid, today):
    """Entrega conselho meteorológico, não um boletim cheio de números."""
    try:
        location = await get_location(db, uid)
        if not location or not location.get("morning_enabled", True):
            return None
        forecast = await fetch_daily_forecast(location, today)
        return forecast_comment(forecast, heading="Hoje", city=location["city"])
    except Exception as exc:
        print(f"[summary] weather-error type={type(exc).__name__} message={str(exc)[:240]}")
        return None


async def _morning_context(db, uid, today):
    weekday = app.WEEKDAY_NAMES[today.weekday()]
    classes = await _rows(
        db.prepare(
            "SELECT s.name,ss.start_time FROM subjects s "
            "JOIN subject_sessions ss ON ss.subject_id=s.id "
            "WHERE s.user_id=? AND s.active=1 AND ss.weekday=? "
            "ORDER BY ss.start_time"
        ).bind(uid, weekday)
    )
    tasks = await _rows(
        db.prepare(
            "SELECT title,due_time FROM daily_items "
            "WHERE user_id=? AND kind='tarefa' AND status='pendente' AND due_date=? "
            "ORDER BY COALESCE(due_time,'99:99'),id"
        ).bind(uid, today.isoformat())
    )
    overdue = await _rows(
        db.prepare(
            "SELECT title FROM daily_items "
            "WHERE user_id=? AND kind='tarefa' AND status='pendente' AND due_date<? "
            "ORDER BY due_date,id LIMIT 3"
        ).bind(uid, today.isoformat())
    )
    return classes, tasks, overdue


def _agenda_brief(classes, tasks, overdue):
    parts = []

    class_names = [_row(item, "name", "") for item in classes]
    if class_names:
        parts.append(
            f"Tem {len(class_names)} aula{'s' if len(class_names) != 1 else ''} hoje: "
            f"{_join_names(class_names)}. Eu te aviso quando estiver chegando a hora."
        )

    untimed = [_row(item, "title", "") for item in tasks if not _row(item, "due_time")]
    timed = [item for item in tasks if _row(item, "due_time")]
    if untimed:
        if len(untimed) == 1:
            parts.append(f"A tarefa sem horário é {_join_names(untimed)}; essa vale deixar no radar.")
        else:
            parts.append(f"As tarefas sem horário são {_join_names(untimed)}; essas valem deixar no radar.")
    if timed:
        parts.append(
            f"As outras {len(timed)} tarefa{'s' if len(timed) != 1 else ''} têm horário; "
            "os lembretes chegam no momento certo."
        )

    if overdue:
        names = [_row(item, "title", "") for item in overdue]
        parts.append(f"Ficou pendente de antes: {_join_names(names)}.")

    if not parts:
        return "A manhã está mais livre por enquanto."
    return " ".join(parts)


async def _morning_text(db, uid, today):
    weather = await _brief_weather(db, uid, today)
    classes, tasks, overdue = await _morning_context(db, uid, today)
    agenda = _agenda_brief(classes, tasks, overdue)

    lines = ["Bom dia, chefe."]
    if weather:
        lines.append(weather)
    lines.append(agenda)
    lines.append("Toca a manhã; se precisar lembrar de algo, dá um salve.")
    return "\n\n".join(lines)


async def _weekly_text(db, uid, today):
    start = today - timedelta(days=6)
    done = await db.prepare(
        "SELECT COUNT(*) n FROM daily_items WHERE user_id=? AND status='concluido' AND date(completed_at)>=?"
    ).bind(uid, start.isoformat()).first()
    pending = await db.prepare(
        "SELECT COUNT(*) n FROM daily_items WHERE user_id=? AND status='pendente' AND due_date<=?"
    ).bind(uid, today.isoformat()).first()
    work = await db.prepare(
        "SELECT COUNT(*) n FROM workout_logs WHERE user_id=? AND status='feito' AND workout_date>=?"
    ).bind(uid, start.isoformat()).first()
    return (
        "📊 Fechamento semanal\n\n"
        f"✅ Tarefas concluídas: {_row(done, 'n', 0)}\n"
        f"📌 Pendências abertas: {_row(pending, 'n', 0)}\n"
        f"🏋️ Treinos feitos: {_row(work, 'n', 0)}\n\n"
        "Boa ou torta, a semana acabou. Segunda a gente finge surpresa e começa de novo. 😏"
    )


async def _send_once(db, token, uid, chat, key, text):
    if await _already_sent(db, uid, key):
        return False

    await _checked_send(token, chat, text)
    await db.prepare(
        "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
    ).bind(uid, key).run()
    return True


async def dispatch_summaries(db, token):
    now = datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    today = now.date()
    users = await _rows(
        db.prepare(
            "SELECT u.id,u.telegram_chat_id,COALESCE(a.day_off,0) day_off "
            "FROM users u LEFT JOIN assistant_state a ON a.user_id=u.id"
        )
    )

    for user in users:
        if int(_row(user, "day_off", 0)):
            continue
        uid = int(_row(user, "id"))
        chat = int(_row(user, "telegram_chat_id"))

        if _within_window(
            now,
            MORNING_SUMMARY_HOUR,
            MORNING_SUMMARY_MINUTE,
            MORNING_RECOVERY_MINUTES,
        ):
            key = f"morning:{today.isoformat()}"
            if not await _already_sent(db, uid, key):
                text = await _morning_text(db, uid, today)
                await _send_once(db, token, uid, chat, key, text)

        if (
            today.weekday() == WEEKLY_SUMMARY_WEEKDAY
            and _within_window(
                now,
                WEEKLY_SUMMARY_HOUR,
                WEEKLY_SUMMARY_MINUTE,
                WEEKLY_GRACE_MINUTES,
            )
        ):
            key = f"weekly:{today.isoformat()}"
            if not await _already_sent(db, uid, key):
                text = await _weekly_text(db, uid, today)
                await _send_once(db, token, uid, chat, key, text)
