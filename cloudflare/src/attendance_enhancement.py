import attendance_patch as attendance
import app
from telegram_api import answer_callback, send_message


def _status_comment(total, limit_value):
    if limit_value is None or int(limit_value) <= 0:
        return None
    limit_value = int(limit_value)
    pct = (total / limit_value) * 100
    if total > limit_value:
        return (
            f"☠️ MATÉRIA PERDIDA POR FALTA: {total}/{limit_value}. "
            "Você plantou falta e conseguiu colher reprovação. Eficiência questionável, mas eficiência."
        )
    if total == limit_value:
        return (
            f"🚨 100% do limite usado ({total}/{limit_value}). Bem, você plantou isso. "
            "Agora se faltar de novo, game over por falta."
        )
    if pct >= 75:
        return (
            f"⚠️ {pct:.0f}% do limite já foi embora. Você está tratando presença como item opcional do plano de ensino. "
            "Eu pisaria no freio antes que a chamada pise em você."
        )
    if pct >= 50:
        return (
            f"⚠️ {pct:.0f}% do limite usado. Eu pararia agora, porque daqui a pouco seu maior inimigo "
            "não vai ser a nota — vai ser a lista de presença."
        )
    if pct >= 30:
        return (
            f"😏 {pct:.0f}% do limite usado. Alguém está se acostumando a não ir e só marcar presença na minha planilha, hein? "
            "É assim que você diz que está aprendendo?"
        )
    if total > 0:
        return f"👀 {pct:.0f}% do limite usado. Ainda está tranquilo. Isso não é um convite para testar até onde vai."
    return None


async def ensure_schema(db):
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS subject_attendance_settings (
            subject_id INTEGER PRIMARY KEY,
            absence_limit INTEGER,
            limit_prompted INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        )
    """).run()
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS subject_absences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            class_date TEXT NOT NULL,
            absence_count INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, session_id, class_date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY(session_id) REFERENCES subject_sessions(id) ON DELETE CASCADE
        )
    """).run()
    await db.prepare("CREATE INDEX IF NOT EXISTS idx_absences_user_subject ON subject_absences(user_id, subject_id, class_date)").run()


async def _enhanced_report(db, uid, subject_id=None):
    await ensure_schema(db)
    if subject_id is not None:
        subject = await attendance._subject_by_id(db, uid, subject_id)
        if not subject:
            return "Não achei essa matéria."
        total = await attendance._total_absences(db, uid, subject_id)
        settings = await attendance._settings(db, subject_id)
        limit_value = attendance._row(settings, "absence_limit") if settings else None
        if limit_value is None:
            return f"📊 {attendance._row(subject,'name')}\n• Faltas: {total}\n• Limite: não informado"
        limit_value = int(limit_value)
        pct = (total / limit_value * 100) if limit_value > 0 else 0
        if total > limit_value:
            remaining_text = "• Situação: ☠️ PERDIDA POR FALTA"
        else:
            remaining_text = f"• Restam: {max(0, limit_value-total)}"
        out = [
            f"📊 {attendance._row(subject,'name')}",
            f"• Faltas: {total}/{limit_value}",
            remaining_text,
            f"• Uso do limite: {pct:.0f}%",
        ]
        comment = _status_comment(total, limit_value)
        if comment:
            out.append(f"\n{comment}")
        return "\n".join(out)

    subjects = await attendance._rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    if not subjects:
        return "📊 Nenhuma matéria ativa cadastrada."
    out = ["📊 Faltas por matéria"]
    for subject in subjects:
        sid = int(attendance._row(subject, "id"))
        total = await attendance._total_absences(db, uid, sid)
        settings = await attendance._settings(db, sid)
        limit_value = attendance._row(settings, "absence_limit") if settings else None
        if limit_value is None:
            out.append(f"• {attendance._row(subject,'name')}: {total} falta(s) — limite não informado")
        else:
            limit_value = int(limit_value)
            tag = " ☠️ PERDIDA POR FALTA" if total > limit_value else ""
            out.append(f"• {attendance._row(subject,'name')}: {total}/{limit_value} falta(s){tag}")
    return "\n".join(out)


async def handle_callback(db, token, callback):
    data = callback.get("data") or ""
    if not data.startswith("att:"):
        return False
    await ensure_schema(db)

    chat_id = ((callback.get("message") or {}).get("chat") or {}).get("id")
    if chat_id is None:
        return True
    uid = await attendance._uid(db, int(chat_id))
    if uid is None:
        return True

    parts = data.split(":")
    if len(parts) != 4:
        await answer_callback(token, callback.get("id"), "Ação inválida.")
        return True
    action, session_id, class_date = parts[1], int(parts[2]), parts[3]
    session = await db.prepare("""
        SELECT ss.id,ss.subject_id,ss.start_time,ss.end_time,s.name
        FROM subject_sessions ss JOIN subjects s ON s.id=ss.subject_id
        WHERE ss.id=? AND s.user_id=?
    """).bind(session_id, uid).first()
    if not session:
        await answer_callback(token, callback.get("id"), "Aula não encontrada.")
        return True

    if action == "go":
        await answer_callback(token, callback.get("id"), "Boa aula.")
        await send_message(token, chat_id, f"✅ Vai para {attendance._row(session,'name')}. Milagre nenhum: só você fazendo o mínimo academicamente esperado. 😌")
        return True
    if action != "skip":
        await answer_callback(token, callback.get("id"), "Ação inválida.")
        return True

    session, created = await attendance._record_absence(db, uid, session_id, class_date)
    if not session:
        await answer_callback(token, callback.get("id"), "Não consegui registrar.")
        return True

    sid = int(attendance._row(session, "subject_id"))
    units = attendance._absence_units(attendance._row(session, "start_time"), attendance._row(session, "end_time"))
    total = await attendance._total_absences(db, uid, sid)
    await answer_callback(token, callback.get("id"), "Falta registrada." if created else "Falta já registrada.")

    settings = await attendance._settings(db, sid)
    limit_value = attendance._row(settings, "absence_limit") if settings else None
    if created:
        msg = f"❌ Falta registrada em {attendance._row(session,'name')}: +{units}. Total agora: {total}"
        if limit_value is not None:
            msg += f"/{int(limit_value)}."
            comment = _status_comment(total, int(limit_value))
            if comment:
                msg += f"\n\n{comment}"
        else:
            msg += "."
    else:
        msg = f"Essa falta de {attendance._row(session,'name')} já estava registrada. Não vou contar duas vezes só porque você resolveu faltar com entusiasmo. 😏"
    await send_message(token, chat_id, msg)

    prompted = int(attendance._row(settings, "limit_prompted", 0) or 0) if settings else 0
    if not prompted:
        await app.set_state(db, uid, "attendance_limit_first", {"subject_id": sid, "subject_name": attendance._row(session, "name")})
        await send_message(
            token,
            chat_id,
            f"Qual é o seu limite de faltas em {attendance._row(session,'name')}?\n"
            "Manda só o número. Se não quiser informar agora, diga `não vou informar`.",
            reply_markup=attendance._kb([["Não vou informar"], ["❌ Cancelar ação"]]),
        )
    return True


def install():
    attendance._attendance_report = _enhanced_report
