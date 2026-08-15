from datetime import datetime, timedelta, timezone

import conversation_layer
import quality_patch
from settings import UTC_OFFSET_HOURS

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
GRACE_MINUTES = 10


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


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


def _inline(rows):
    return {"inline_keyboard": [[{"text": label, "callback_data": data} for label, data in row] for row in rows]}


async def dispatch_due_reminders(db, token):
    """Dispara lembretes por janela de tolerância, não por igualdade exata de minuto.

    Isso torna o cron resiliente a atrasos de execução e a falhas pontuais de outros schedulers.
    A chave de notification_log continua garantindo idempotência.
    """
    now = _now()
    today = now.date()

    users = await _rows(db.prepare(
        "SELECT u.id,u.telegram_chat_id,a.day_off FROM users u "
        "JOIN assistant_state a ON a.user_id=u.id"
    ))

    for user in users:
        if int(_row(user, "day_off", 0)):
            continue
        uid = int(_row(user, "id"))
        chat = int(_row(user, "telegram_chat_id"))

        items = await _rows(db.prepare(
            "SELECT id,kind,title,details,due_time FROM daily_items "
            "WHERE user_id=? AND status='pendente' AND due_date=? AND due_time IS NOT NULL"
        ).bind(uid, today.isoformat()))

        for item in items:
            iid = int(_row(item, "id"))
            kind = _row(item, "kind")
            details = _row(item, "details") or ""

            # Provas têm scheduler acadêmico próprio e não entram na regra 10/5.
            if details.startswith("exam:"):
                continue

            simple = details == "simple_reminder"
            try:
                h, m = map(int, _row(item, "due_time").split(":"))
            except Exception:
                continue

            due = datetime.combine(today, datetime.min.time()).replace(
                hour=h, minute=m, tzinfo=LOCAL_TZ
            )
            advance = 0 if simple else (10 if kind == "tarefa" else 5)
            desired = due - timedelta(minutes=advance)
            late = now - desired

            # Ainda não chegou ou já passou demais da janela de recuperação.
            if late.total_seconds() < 0 or late > timedelta(minutes=GRACE_MINUTES):
                continue

            key = f"item:new:{iid}:{today}:{desired.strftime('%H:%M')}"
            exists = await db.prepare(
                "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
            ).bind(uid, key).first()
            if exists:
                continue

            if simple:
                markup = _inline([[("👌 Entendi", f"item:done:{iid}")]])
                text = f"🔔 {_row(item,'title')} — {_row(item,'due_time')}. Só um aviso."
            elif kind == "tarefa":
                markup = _inline([
                    [("✅ Feito", f"item:done:{iid}"), ("⏰ +30 min", f"item:snooze:{iid}:30")],
                    [("🚫 Cancelar", f"item:cancel:{iid}")],
                ])
                text = f"✅ {_row(item,'title')} às {_row(item,'due_time')}. Faltam 10 minutos. Dá tempo de parar de fingir que esqueceu. 😌"
            else:
                markup = _inline([
                    [("👌 Ciente", f"item:done:{iid}"), ("⏰ +30 min", f"item:snooze:{iid}:30")]
                ])
                text = f"📅 {_row(item,'title')} às {_row(item,'due_time')}. Faltam 5 minutos. Se organize."

            await conversation_layer._remember(db, uid, "lembrete" if simple else kind, iid)
            # quality_patch.send_message já passa pela personalidade variada instalada.
            await quality_patch.send_message(token, chat, text, reply_markup=markup)
            await db.prepare(
                "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
            ).bind(uid, key).run()

            if simple:
                await db.prepare(
                    "UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP WHERE id=?"
                ).bind(iid).run()
