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


async def _morning_text(db, uid, today):
    text = await app.agenda_text(db, uid, today, True)
    grocery = await _rows(
        db.prepare("SELECT name FROM grocery_items WHERE user_id=? AND missing=1 ORDER BY name LIMIT 5").bind(uid)
    )
    extra = ""
    if grocery:
        extra = "\n\n🛒 Faltando em casa: " + ", ".join(_row(r, "name") for r in grocery)

    yesterday = today - timedelta(days=1)
    pending = await _rows(
        db.prepare(
            "SELECT title FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente' AND due_date=?"
        ).bind(uid, yesterday.isoformat())
    )
    if pending:
        extra += (
            "\n\n📎 Ontem deixou herança:\n"
            + "\n".join(f"• {_row(r, 'title')}" for r in pending)
            + "\nElas sobreviveram à virada do dia. Impressionante persistência."
        )

    return (
        "☀️ Resumo da manhã\n\n"
        + text
        + extra
        + "\n\nNada demais. Só a administração básica de uma pequena empresa chamada sua vida. 😌"
    )


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
    existing = await db.prepare(
        "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
    ).bind(uid, key).first()
    if existing:
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

        # O resumo é nominalmente das 07:00, mas se o cron/deploy/Telegram falhar
        # nessa janela o Butler continua tentando ao longo da manhã. O log por
        # chave diária impede duplicação assim que uma entrega é confirmada.
        if _within_window(
            now,
            MORNING_SUMMARY_HOUR,
            MORNING_SUMMARY_MINUTE,
            MORNING_RECOVERY_MINUTES,
        ):
            key = f"morning:{today.isoformat()}"
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
            text = await _weekly_text(db, uid, today)
            await _send_once(db, token, uid, chat, key, text)
