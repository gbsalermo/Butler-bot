"""Scheduler autoritativo de tarefas, compromissos e lembretes simples.

Chamado por: ``entry.Default.scheduled`` no subsistema ``daily_items``.

Política atual:
- tarefa: avisa no horário configurado;
- compromisso: avisa 5 minutos antes;
- lembrete simples: avisa no horário, aceitando no máximo 2 minutos de atraso;
- ``notification_log`` impede duplicidade;
- Day-off bloqueia itens normais, mas lembrete pessoal simples continua válido.
"""

from datetime import datetime, timedelta, timezone

import conversation_layer
import notification_ack
import quality_patch
from maintenance import run_maintenance
from settings import UTC_OFFSET_HOURS

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
GRACE_MINUTES = 10
STRICT_REMINDER_DELAY_MINUTES = 2


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
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": data} for label, data in row]
            for row in rows
        ]
    }


async def _suppress_legacy_item_scheduler(db, uid, iid, today, due, kind):
    legacy_advance = 10 if kind == "compromisso" else 0
    legacy_target = due - timedelta(minutes=legacy_advance)
    legacy_key = f"item:{iid}:{today}:{legacy_target.strftime('%H:%M')}"
    await db.prepare(
        "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
    ).bind(uid, legacy_key).run()


async def dispatch_due_reminders(db, token):
    try:
        await run_maintenance(db, token)
    except Exception as exc:
        print(f"[maintenance] error type={type(exc).__name__} message={str(exc)[:240]}")

    now = _now()
    today = now.date()
    users = await _rows(
        db.prepare(
            "SELECT u.id,u.telegram_chat_id,COALESCE(a.day_off,0) day_off "
            "FROM users u LEFT JOIN assistant_state a ON a.user_id=u.id"
        )
    )

    for user in users:
        uid = int(_row(user, "id"))
        chat = int(_row(user, "telegram_chat_id"))
        day_off = bool(int(_row(user, "day_off", 0)))

        items = await _rows(
            db.prepare(
                "SELECT id,kind,title,details,due_time FROM daily_items "
                "WHERE user_id=? AND status='pendente' AND due_date=? "
                "AND due_time IS NOT NULL"
            ).bind(uid, today.isoformat())
        )

        for item in items:
            iid = int(_row(item, "id"))
            kind = _row(item, "kind")
            details = _row(item, "details") or ""
            if details.startswith("exam:"):
                continue

            simple = details == "simple_reminder"
            try:
                h, m = map(int, _row(item, "due_time").split(":"))
            except Exception:
                continue

            due = datetime.combine(today, datetime.min.time()).replace(
                hour=h,
                minute=m,
                tzinfo=LOCAL_TZ,
            )
            await _suppress_legacy_item_scheduler(db, uid, iid, today, due, kind)

            if day_off and not simple:
                continue

            advance = 5 if (kind == "compromisso" and not simple) else 0
            desired = due - timedelta(minutes=advance)
            late = now - desired
            if late.total_seconds() < 0:
                continue

            is_task = kind == "tarefa"
            if simple and late > timedelta(minutes=STRICT_REMINDER_DELAY_MINUTES):
                continue
            if not simple and not is_task and late > timedelta(minutes=GRACE_MINUTES):
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
            elif is_task:
                markup = _inline(
                    [
                        [
                            ("✅ Feito", f"item:done:{iid}"),
                            ("⏰ +30 min", f"item:snooze:{iid}:30"),
                        ],
                        [("🚫 Cancelar", f"item:cancel:{iid}")],
                    ]
                )
                if late > timedelta(minutes=2):
                    minutes = max(1, int(late.total_seconds() // 60))
                    text = (
                        f"✅ {_row(item,'title')} — era para {_row(item,'due_time')}. "
                        f"O aviso atrasou {minutes} min, mas a tarefa continua pendente "
                        "até você concluir ou cancelar."
                    )
                else:
                    text = (
                        f"✅ {_row(item,'title')} — {_row(item,'due_time')}. Chegou a hora. "
                        "Agora a tarefa saiu oficialmente da categoria 'problema do eu do futuro'. 😏"
                    )
            else:
                markup = _inline(
                    [[("👌 Ciente", f"item:done:{iid}"), ("⏰ +30 min", f"item:snooze:{iid}:30")]]
                )
                text = f"📅 {_row(item,'title')} às {_row(item,'due_time')}. Faltam 5 minutos. Se organize."

            await conversation_layer._remember(
                db,
                uid,
                "lembrete" if simple else kind,
                iid,
            )

            await quality_patch.send_message(token, chat, text, reply_markup=markup)
            await db.prepare(
                "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
            ).bind(uid, key).run()

            if simple:
                await db.prepare(
                    "UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP WHERE id=?"
                ).bind(iid).run()
                await notification_ack.remember_notification(
                    db, uid, "simple_reminder", iid, _row(item, "title")
                )
