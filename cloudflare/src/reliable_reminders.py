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
    """Dispara notificações pendentes de forma idempotente e resiliente.

    Política:
    - lembrete simples explícito: deve chegar mesmo em Day-off e, se o cron atrasar,
      faz catch-up durante o mesmo dia em vez de desaparecer;
    - tarefa: horário exato com tolerância curta;
    - compromisso: 5 minutos antes com tolerância curta;
    - notification_log impede duplicidade.

    Um lembrete explícito é mais próximo de um alarme pedido pelo usuário do que de
    uma cobrança do Butler. Por isso Day-off silencia cobranças, mas não o aviso que
    o próprio usuário pediu para determinado horário.
    """
    now = _now()
    today = now.date()

    users = await _rows(db.prepare(
        "SELECT u.id,u.telegram_chat_id,a.day_off FROM users u "
        "JOIN assistant_state a ON a.user_id=u.id"
    ))

    for user in users:
        uid = int(_row(user, "id"))
        chat = int(_row(user, "telegram_chat_id"))
        day_off = bool(int(_row(user, "day_off", 0)))

        items = await _rows(db.prepare(
            "SELECT id,kind,title,details,due_time FROM daily_items "
            "WHERE user_id=? AND status='pendente' AND due_date=? AND due_time IS NOT NULL"
        ).bind(uid, today.isoformat()))

        for item in items:
            iid = int(_row(item, "id"))
            kind = _row(item, "kind")
            details = _row(item, "details") or ""

            # Provas têm scheduler acadêmico próprio.
            if details.startswith("exam:"):
                continue

            simple = details == "simple_reminder"

            # Day-off bloqueia cobranças operacionais, mas não um lembrete pontual
            # explicitamente pedido pelo usuário.
            if day_off and not simple:
                continue

            try:
                h, m = map(int, _row(item, "due_time").split(":"))
            except Exception:
                continue

            due = datetime.combine(today, datetime.min.time()).replace(
                hour=h, minute=m, tzinfo=LOCAL_TZ
            )
            advance = 5 if (kind == "compromisso" and not simple) else 0
            desired = due - timedelta(minutes=advance)
            late = now - desired

            if late.total_seconds() < 0:
                continue

            # Para lembrete explícito não existe janela fatal de 10 minutos: se não
            # foi enviado, faz catch-up no mesmo dia. Tarefa/compromisso mantêm a
            # tolerância curta para não gerar cobranças antigas horas depois.
            if not simple and late > timedelta(minutes=GRACE_MINUTES):
                continue

            key = f"item:new:{iid}:{today}:{desired.strftime('%H:%M')}"
            exists = await db.prepare(
                "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
            ).bind(uid, key).first()
            if exists:
                continue

            if simple:
                markup = _inline([[("👌 Entendi", f"item:done:{iid}")]])
                if late > timedelta(minutes=2):
                    minutes = max(1, int(late.total_seconds() // 60))
                    text = (
                        f"🔔 {_row(item,'title')} — era para {_row(item,'due_time')}. "
                        f"Cheguei {minutes} min atrasado nesse aviso; não vou fingir que não aconteceu."
                    )
                else:
                    text = f"🔔 {_row(item,'title')} — {_row(item,'due_time')}. Só um aviso."
            elif kind == "tarefa":
                markup = _inline([
                    [("✅ Feito", f"item:done:{iid}"), ("⏰ +30 min", f"item:snooze:{iid}:30")],
                    [("🚫 Cancelar", f"item:cancel:{iid}")],
                ])
                text = f"✅ {_row(item,'title')} — {_row(item,'due_time')}. Chegou a hora. Agora a tarefa saiu oficialmente da categoria 'problema do eu do futuro'. 😏"
            else:
                markup = _inline([
                    [("👌 Ciente", f"item:done:{iid}"), ("⏰ +30 min", f"item:snooze:{iid}:30")]
                ])
                text = f"📅 {_row(item,'title')} às {_row(item,'due_time')}. Faltam 5 minutos. Se organize."

            await conversation_layer._remember(db, uid, "lembrete" if simple else kind, iid)
            await quality_patch.send_message(token, chat, text, reply_markup=markup)
            await db.prepare(
                "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
            ).bind(uid, key).run()

            if simple:
                await db.prepare(
                    "UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP WHERE id=?"
                ).bind(iid).run()
