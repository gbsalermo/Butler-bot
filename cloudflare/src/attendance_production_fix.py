from datetime import datetime, timedelta

import app
import attendance_patch as attendance
from telegram_api import send_message

# Os primeiros 10 minutos continuam sendo a janela "normal". Se o Worker perder
# essa janela, o alerta ainda pode ser recuperado enquanto a aula estiver em andamento.
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


def _session_bounds(now, start_text, end_text):
    """Retorna início/fim locais da sessão no dia de hoje.

    Se o horário final estiver ausente ou inválido, usa uma recuperação conservadora
    de 60 minutos após o início em vez de perder o alerta definitivamente.
    """
    h, m = map(int, start_text.split(":"))
    start = now.replace(hour=h, minute=m, second=0, microsecond=0)

    try:
        eh, em = map(int, (end_text or "").split(":"))
        end = now.replace(hour=eh, minute=em, second=0, microsecond=0)
        if end <= start:
            end += timedelta(days=1)
    except Exception:
        end = start + timedelta(minutes=60)

    return start, end


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
        ORDER BY ss.start_time
    """).bind(weekday))

    for session in sessions:
        start_text = attendance._row(session, "start_time")
        end_text = attendance._row(session, "end_time")
        if not start_text:
            continue

        try:
            target, end_target = _session_bounds(now, start_text, end_text)
        except Exception:
            continue

        # Nunca dispara antes da aula. Depois do início, continua recuperável enquanto
        # a aula estiver acontecendo. Isso evita perder a chamada por atraso de cron,
        # deploy ou falha temporária do Worker/Telegram.
        if now < target or now >= end_target:
            continue

        delay_minutes = max(0, int((now - target).total_seconds() / 60))

        uid = int(attendance._row(session, "user_id"))
        key = f"attendance:{today}:{attendance._row(session,'id')}"
        sent = await db.prepare(
            "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
        ).bind(uid, key).first()
        if sent:
            continue

        chat_id = int(attendance._row(session, "telegram_chat_id"))
        if delay_minutes <= 0:
            late_note = ""
        elif delay_minutes <= ATTENDANCE_GRACE_MINUTES:
            late_note = (
                f"\n(O cron chegou {delay_minutes} min atrasado, mas eu não vou usar isso "
                "como desculpa pra faltar por você.)"
            )
        else:
            late_note = (
                f"\n⚠️ O aviso atrasou {delay_minutes} min. A aula ainda está acontecendo, "
                "então recuperei a chamada em vez de fingir que ela nunca existiu."
            )

        # scheduled_delivery_guard troca este send_message por uma versão que lança
        # exceção quando o Telegram não confirma a entrega. Assim o log só é gravado
        # depois de um envio realmente aceito e o próximo cron pode tentar novamente.
        await send_message(
            token,
            chat_id,
            f"🎓 Aula agora: {attendance._row(session,'name')} — {start_text}–{end_text}"
            + (f" ({attendance._row(session,'location')})" if attendance._row(session, "location") else "")
            + "\nVocê vai?"
            + late_note,
            reply_markup=attendance._inline(int(attendance._row(session, "id")), today),
        )
        await db.prepare(
            "INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)"
        ).bind(uid, key).run()
