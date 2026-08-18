from datetime import datetime, timedelta

import app
import attendance_patch as attendance
from telegram_api import send_message

# Regra global para TODAS as aulas ativas, independentemente de terem sido
# pré-cadastradas, importadas ou criadas depois pelo usuário.
PRE_CLASS_MINUTES = 10
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


async def _already_sent(db, uid, *keys):
    for key in keys:
        row = await db.prepare(
            "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
        ).bind(uid, key).first()
        if row:
            return True
    return False


async def _mark_sent(db, uid, key):
    await db.prepare(
        "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
    ).bind(uid, key).run()


async def _heartbeat(db, now, weekday, session_count):
    """Guarda evidência real de que o scheduler acadêmico executou naquele minuto."""
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS attendance_scheduler_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ran_at_local TEXT NOT NULL,
            weekday TEXT NOT NULL,
            session_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """).run()
    await db.prepare(
        "INSERT INTO attendance_scheduler_ticks(ran_at_local,weekday,session_count) VALUES(?,?,?)"
    ).bind(now.strftime("%Y-%m-%d %H:%M"), weekday, int(session_count)).run()
    # Quatro horas de ticks são suficientes para diagnosticar pré-aviso e início
    # sem transformar o heartbeat em histórico infinito.
    await db.prepare("""
        DELETE FROM attendance_scheduler_ticks
        WHERE id NOT IN (
            SELECT id FROM attendance_scheduler_ticks ORDER BY id DESC LIMIT 240
        )
    """).run()


async def _dispatch_pre(db, token, session, uid, chat_id, sid, today, now, start_target, end_text):
    pre_target = start_target - timedelta(minutes=PRE_CLASS_MINUTES)
    if not (pre_target <= now < start_target):
        return

    pre_key = f"attendance:pre:{today}:{sid}"
    if await _already_sent(db, uid, pre_key):
        return

    minutes = max(0, int((start_target - now).total_seconds() / 60))
    await send_message(
        token,
        chat_id,
        f"⏰ Aula em {minutes if minutes else 'menos de 1'} min: "
        f"{attendance._row(session,'name')} — {attendance._row(session,'start_time')}–{end_text}"
        + (f" ({attendance._row(session,'location')})" if attendance._row(session, "location") else "")
        + "\nVai ajeitando as coisas. O conhecimento infelizmente ainda exige presença física às vezes.",
    )
    await _mark_sent(db, uid, pre_key)


async def _dispatch_start(db, token, session, uid, chat_id, sid, today, now, start_target, end_target, end_text):
    if not (start_target <= now < end_target):
        return

    start_key = f"attendance:start:{today}:{sid}"
    legacy_key = f"attendance:{today}:{sid}"
    if await _already_sent(db, uid, start_key, legacy_key):
        return

    delay_minutes = max(0, int((now - start_target).total_seconds() / 60))
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
            "então recuperei a chamada; isso é contingência, não o comportamento esperado."
        )

    await send_message(
        token,
        chat_id,
        f"🎓 Aula agora: {attendance._row(session,'name')} — {attendance._row(session,'start_time')}–{end_text}"
        + (f" ({attendance._row(session,'location')})" if attendance._row(session, "location") else "")
        + "\nVocê vai?"
        + late_note,
        reply_markup=attendance._inline(sid, today),
    )
    await _mark_sent(db, uid, start_key)


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

    # O heartbeat acontece antes de qualquer envio. Assim até uma falha no Telegram
    # deixa evidência de que o cron acadêmico realmente executou naquele minuto.
    try:
        await _heartbeat(db, now, weekday, len(sessions))
    except Exception as exc:
        print(f"[attendance-heartbeat] error type={type(exc).__name__} message={str(exc)[:300]}")

    # Uma matéria nunca pode derrubar os avisos das outras.
    for session in sessions:
        sid = attendance._row(session, "id")
        try:
            sid = int(sid)
            uid = int(attendance._row(session, "user_id"))
            chat_id = int(attendance._row(session, "telegram_chat_id"))
            start_text = attendance._row(session, "start_time")
            end_text = attendance._row(session, "end_time")
            if not start_text:
                continue
            start_target, end_target = _session_bounds(now, start_text, end_text)

            try:
                await _dispatch_pre(
                    db, token, session, uid, chat_id, sid, today, now, start_target, end_text
                )
            except Exception as exc:
                print(
                    f"[attendance-pre] error session_id={sid} user_id={uid} "
                    f"type={type(exc).__name__} message={str(exc)[:300]}"
                )

            try:
                await _dispatch_start(
                    db, token, session, uid, chat_id, sid, today, now,
                    start_target, end_target, end_text
                )
            except Exception as exc:
                print(
                    f"[attendance-start] error session_id={sid} user_id={uid} "
                    f"type={type(exc).__name__} message={str(exc)[:300]}"
                )
        except Exception as exc:
            print(
                f"[attendance-session] error session_id={sid} "
                f"type={type(exc).__name__} message={str(exc)[:300]}"
            )
            continue
