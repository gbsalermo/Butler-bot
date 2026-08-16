from datetime import date, datetime, timedelta

import academic_intelligence as academic
from telegram_api import delivery_error, delivery_ok, send_message

GRACE_MINUTES = 10


def _row(row, key, default=None):
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _checked_send(token, chat, text):
    result = await send_message(token, chat, text, reply_markup=_kb(academic.ACADEMIC_KB))
    if not delivery_ok(result):
        error = delivery_error(result)
        print(f"[exam-delivery] failed chat_id={chat} error={error}")
        raise RuntimeError(f"Telegram não confirmou alerta de prova: {error}")
    return result


def _within(now, target):
    delta = now - target
    return timedelta(0) <= delta <= timedelta(minutes=GRACE_MINUTES)


async def exam_reminders(db, token):
    now = academic._now()
    today = now.date()
    users = await academic._rows(db.prepare(
        "SELECT u.id,u.telegram_chat_id,a.day_off FROM users u JOIN assistant_state a ON a.user_id=u.id"
    ))
    for user in users:
        if int(_row(user, "day_off", 0) or 0):
            continue
        uid = int(_row(user, "id")); chat = int(_row(user, "telegram_chat_id"))
        exams = await academic._rows(db.prepare(
            "SELECT id,title,due_date,due_time FROM daily_items "
            "WHERE user_id=? AND status='pendente' AND details LIKE 'exam:%' AND due_date>=?"
        ).bind(uid, today.isoformat()))
        for exam in exams:
            d = date.fromisoformat(_row(exam, "due_date")); days = (d - today).days; iid = int(_row(exam, "id"))
            moments = []

            if days in (7, 3, 1):
                target = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if _within(now, target):
                    moments.append((f"d{days}", f"📝 {_row(exam,'title')} em {days} dia{'s' if days != 1 else ''}."))

            if days == 0:
                morning = now.replace(hour=7, minute=30, second=0, microsecond=0)
                if _within(now, morning):
                    moments.append((
                        "today",
                        f"📝 É hoje: {_row(exam,'title')}" + (f" às {_row(exam,'due_time')}" if _row(exam,'due_time') else "") + ". Agora fingir surpresa exigiria atuação demais até para você. 😌"
                    ))

                if _row(exam, "due_time"):
                    try:
                        h, m = map(int, _row(exam, "due_time").split(":"))
                        exam_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                        one_hour = exam_dt - timedelta(hours=1)
                        if _within(now, one_hour):
                            moments.append(("h1", f"⏰ {_row(exam,'title')} em 1 hora. Revisão final, água e dignidade. Nessa ordem se possível. 😏"))
                    except Exception:
                        pass

            for code, msg in moments:
                key = f"exam:{iid}:{d.isoformat()}:{code}"
                exists = await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid, key).first()
                if exists:
                    continue
                await _checked_send(token, chat, msg)
                await db.prepare("INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid, key).run()
