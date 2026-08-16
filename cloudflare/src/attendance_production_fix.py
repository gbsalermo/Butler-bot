from datetime import datetime, timedelta

import app
import attendance_patch as attendance
from telegram_api import send_message

ATTENDANCE_GRACE_MINUTES = 10

ACADEMIC_KB_FULL = [
    ["📚 Minhas matérias", "⚙️ Gerenciar matérias"],
    ["📝 Adicionar prova", "📋 Provas"],
    ["📊 Ver faltas", "⚙️ Limite de faltas"],
    ["✏️ Editar limite", "🗑️ Excluir falta"],
    ["📥 Importar grade por PDF/texto"],
    ["🏠 Menu principal"],
]


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


def install():
    # Fonte autoritativa para os dois módulos que exibem o menu acadêmico.
    try:
        app.ACADEMIC_KB[:] = [list(row) for row in ACADEMIC_KB_FULL]
    except Exception:
        pass
    try:
        import academic_intelligence
        academic_intelligence.ACADEMIC_KB[:] = [list(row) for row in ACADEMIC_KB_FULL]
    except Exception:
        pass


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    if text not in {"📚 Matérias", "⬅️ Voltar às matérias"}:
        return False
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    await send_message(
        token,
        int(chat_id),
        "📚 Matérias. Provas, faltas e aquela delicada arte de aparecer na aula ficam por aqui.",
        reply_markup=_kb(ACADEMIC_KB_FULL),
    )
    return True


async def dispatch_class_attendance_reliable(db, token):
    now = attendance._now()
    weekday = app.WEEKDAY_NAMES[now.weekday()]
    today = now.date().isoformat()
    sessions = await attendance._rows(db.prepare("""
        SELECT ss.id,ss.start_time,ss.end_time,ss.location,s.name,u.id user_id,u.telegram_chat_id
        FROM subject_sessions ss
        JOIN subjects s ON s.id=ss.subject_id
        JOIN users u ON u.id=s.user_id
        WHERE s.active=1 AND ss.weekday=?
    """).bind(weekday))

    for session in sessions:
        start_text = attendance._row(session, "start_time")
        if not start_text:
            continue
        try:
            h, m = map(int, start_text.split(":"))
        except Exception:
            continue
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delay_minutes = (now - target).total_seconds() / 60
        # Não dispara antes da aula; recupera ticks atrasados por até 10 minutos.
        if delay_minutes < 0 or delay_minutes > ATTENDANCE_GRACE_MINUTES:
            continue

        uid = int(attendance._row(session, "user_id"))
        key = f"attendance:{today}:{attendance._row(session,'id')}"
        sent = await db.prepare(
            "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
        ).bind(uid, key).first()
        if sent:
            continue

        chat_id = int(attendance._row(session, "telegram_chat_id"))
        late = int(delay_minutes)
        late_note = "" if late <= 0 else f"\n(O cron chegou {late} min atrasado, mas eu não vou usar isso como desculpa pra faltar por você.)"
        await send_message(
            token,
            chat_id,
            f"🎓 Aula agora: {attendance._row(session,'name')} — {start_text}–{attendance._row(session,'end_time')}"
            + (f" ({attendance._row(session,'location')})" if attendance._row(session, "location") else "")
            + "\nVocê vai?"
            + late_note,
            reply_markup=attendance._inline(int(attendance._row(session, "id")), today),
        )
        await db.prepare(
            "INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)"
        ).bind(uid, key).run()
