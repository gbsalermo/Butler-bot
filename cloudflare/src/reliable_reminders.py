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


async def _suppress_legacy_item_scheduler(db, uid, iid, today, due, kind):
    """Marca a chave usada pelo scheduler antigo de app.py.

    O dispatcher oficial de daily_items é este módulo. Enquanto o scheduler legado
    ainda existir em app.py para resumos/aulas, gravamos sua chave de item para ele
    não emitir uma segunda mensagem no mesmo ciclo.
    """
    legacy_advance = 10 if kind == "compromisso" else 0
    legacy_target = due - timedelta(minutes=legacy_advance)
    legacy_key = f"item:{iid}:{today}:{legacy_target.strftime('%H:%M')}"
    await db.prepare(
        "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
    ).bind(uid, legacy_key).run()


async def dispatch_due_reminders(db, token):
    """Dispara notificações pendentes de forma idempotente e resiliente.

    Política:
    - lembrete simples explícito: avisa no horário e faz catch-up no mesmo dia;
    - tarefa com horário: avisa no horário e também faz catch-up no mesmo dia se o
      cron/deploy perder a janela original; continua pendente até conclusão/cancelamento;
    - compromisso: 5 minutos antes, com tolerância curta para não avisar evento velho;
    - Day-off silencia tarefa/compromisso, mas não lembrete simples explícito;
    - notification_log impede duplicidade;
    - o scheduler legado de app.py é silenciado para daily_items, evitando aviso duplo.
    """
    now = _now()
    today = now.date()

    users = await _rows(db.prepare(
        "SELECT u.id,u.telegram_chat_id,COALESCE(a.day_off,0) day_off FROM users u "
        "LEFT JOIN assistant_state a ON a.user_id=u.id"
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

            # Sempre neutraliza o caminho legado antes que app.scheduled_tick rode.
            # Isso vale inclusive antes do horário oficial do aviso.
            await _suppress_legacy_item_scheduler(db, uid, iid, today, due, kind)

            if day_off and not simple:
                continue

            advance = 5 if (kind == "compromisso" and not simple) else 0
            desired = due - timedelta(minutes=advance)
            late = now - desired

            if late.total_seconds() < 0:
                continue

            is_task = kind == "tarefa"
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
                if late > timedelta(minutes=2):
                    minutes = max(1, int(late.total_seconds() // 60))
                    text = (
                        f"🔔 {_row(item,'title')} — era para {_row(item,'due_time')}. "
                        f"Cheguei {minutes} min atrasado nesse aviso; não vou fingir que não aconteceu."
                    )
                else:
                    text = f"🔔 {_row(item,'title')} — {_row(item,'due_time')}. Só um aviso."
            elif is_task:
                markup = _inline([
                    [("✅ Feito", f"item:done:{iid}"), ("⏰ +30 min", f"item:snooze:{iid}:30")],
                    [("🚫 Cancelar", f"item:cancel:{iid}")],
                ])
                if late > timedelta(minutes=2):
                    minutes = max(1, int(late.total_seconds() // 60))
                    text = (
                        f"✅ {_row(item,'title')} — era para {_row(item,'due_time')}. "
                        f"O aviso atrasou {minutes} min, mas a tarefa continua pendente até você concluir ou cancelar."
                    )
                else:
                    text = (
                        f"✅ {_row(item,'title')} — {_row(item,'due_time')}. Chegou a hora. "
                        "Agora a tarefa saiu oficialmente da categoria 'problema do eu do futuro'. 😏"
                    )
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
