from datetime import date, timedelta

import academic_intelligence as academic
from telegram_api import delivery_error, delivery_ok, send_message



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


def _at_or_after(now, hour, minute=0):
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return now >= target


def _exam_datetime(now, due_time):
    if not due_time:
        return None
    try:
        h, m = map(int, due_time.split(":"))
        return now.replace(hour=h, minute=m, second=0, microsecond=0)
    except Exception:
        return None


def _minutes_until(now, target):
    seconds = max(0, int((target - now).total_seconds()))
    return max(1, (seconds + 59) // 60)


async def exam_reminders(db, token):
    """Envia lembretes de prova com recuperação no mesmo dia.

    Antes, avisos de 7/3/1 dias dependiam de o cron acertar uma janela de apenas
    dez minutos às 09:00. Uma prova cadastrada depois desse horário nunca recebia
    o aviso da véspera. Agora cada marco pode ser recuperado até o fim do próprio
    dia, sem duplicar graças ao ``notification_log``.
    """
    now = academic._now()
    today = now.date()
    users = await academic._rows(db.prepare(
        "SELECT u.id,u.telegram_chat_id,a.day_off FROM users u JOIN assistant_state a ON a.user_id=u.id"
    ))
    for user in users:
        if int(_row(user, "day_off", 0) or 0):
            continue
        uid = int(_row(user, "id"))
        chat = int(_row(user, "telegram_chat_id"))
        exams = await academic._rows(db.prepare(
            "SELECT id,title,due_date,due_time FROM daily_items "
            "WHERE user_id=? AND status='pendente' AND details LIKE 'exam:%' AND due_date>=?"
        ).bind(uid, today.isoformat()))

        for exam in exams:
            d = date.fromisoformat(_row(exam, "due_date"))
            days = (d - today).days
            iid = int(_row(exam, "id"))
            due_time = _row(exam, "due_time")
            exam_dt = _exam_datetime(now, due_time) if days == 0 else None
            moments = []

            # Marcos de antecedência: se o cron ou o cadastro perderam 09:00,
            # recupera no restante do mesmo dia em vez de perder o lembrete.
            if days in (7, 3, 1) and _at_or_after(now, 9, 0):
                if days == 1:
                    msg = f"📝 Amanhã: {_row(exam,'title')}" + (f" às {due_time}" if due_time else "") + "."
                else:
                    msg = f"📝 {_row(exam,'title')} em {days} dias."
                moments.append((f"d{days}", msg))

            if days == 0:
                # Aviso da manhã também pode ser recuperado, mas nunca depois do
                # horário da prova quando ele é conhecido.
                before_exam = exam_dt is None or now < exam_dt
                in_last_hour = exam_dt is not None and (exam_dt - timedelta(hours=1)) <= now < exam_dt
                if _at_or_after(now, 7, 30) and before_exam and not in_last_hour:
                    moments.append((
                        "today",
                        f"📝 É hoje: {_row(exam,'title')}" + (f" às {due_time}" if due_time else "") + "."
                    ))

                # O lembrete de 1h agora se recupera até a hora da prova. Se o cron
                # atrasou alguns minutos, a mensagem informa o tempo real restante.
                if in_last_hour:
                    minutes = _minutes_until(now, exam_dt)
                    when = "1 hora" if minutes >= 60 else f"{minutes} min"
                    moments.append(("h1", f"⏰ {_row(exam,'title')} em {when}. Revisão final e material separado."))

            for code, msg in moments:
                key = f"exam:{iid}:{d.isoformat()}:{code}"
                exists = await db.prepare(
                    "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
                ).bind(uid, key).first()
                if exists:
                    continue
                await _checked_send(token, chat, msg)
                await db.prepare(
                    "INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)"
                ).bind(uid, key).run()
