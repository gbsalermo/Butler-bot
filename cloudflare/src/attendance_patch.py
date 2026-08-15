import math
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import app
from settings import UTC_OFFSET_HOURS
from telegram_api import answer_callback, send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))

ATTENDANCE_KB = [
    ["📊 Ver faltas", "⚙️ Limite de faltas"],
    ["⬅️ Voltar às matérias"],
]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


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


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


def _inline(session_id, class_date):
    return {
        "inline_keyboard": [[
            {"text": "✅ Vou", "callback_data": f"att:go:{session_id}:{class_date}"},
            {"text": "❌ Não vou", "callback_data": f"att:skip:{session_id}:{class_date}"},
        ]]
    }


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


def _absence_units(start_time, end_time):
    sh, sm = map(int, start_time.split(":"))
    eh, em = map(int, end_time.split(":"))
    minutes = (eh * 60 + em) - (sh * 60 + sm)
    if minutes <= 0:
        minutes += 24 * 60
    return max(1, int(math.ceil(minutes / 60)))


async def _subject_by_id(db, uid, subject_id):
    return await db.prepare("SELECT id,name,active FROM subjects WHERE id=? AND user_id=?").bind(subject_id, uid).first()


async def _subject_by_text(db, uid, text):
    subjects = await _rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    n = _norm(text)
    exact = [s for s in subjects if _norm(_row(s, "name")) == n]
    if exact:
        return exact[0], subjects
    matches = [s for s in subjects if _norm(_row(s, "name")) in n or n in _norm(_row(s, "name"))]
    return (matches[0] if len(matches) == 1 else None), subjects


async def _subject_keyboard(db, uid):
    subjects = await _rows(db.prepare("SELECT name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    names = [_row(s, "name") for s in subjects]
    rows = [[name] for name in names]
    rows.append(["❌ Cancelar ação"])
    return rows


async def _settings(db, subject_id):
    return await db.prepare("SELECT absence_limit,limit_prompted FROM subject_attendance_settings WHERE subject_id=?").bind(subject_id).first()


async def _set_limit(db, subject_id, value):
    await db.prepare("""
        INSERT INTO subject_attendance_settings(subject_id,absence_limit,limit_prompted,updated_at)
        VALUES(?,?,1,CURRENT_TIMESTAMP)
        ON CONFLICT(subject_id) DO UPDATE SET
          absence_limit=excluded.absence_limit,
          limit_prompted=1,
          updated_at=CURRENT_TIMESTAMP
    """).bind(subject_id, value).run()


async def _mark_prompted_without_limit(db, subject_id):
    await db.prepare("""
        INSERT INTO subject_attendance_settings(subject_id,absence_limit,limit_prompted,updated_at)
        VALUES(?,NULL,1,CURRENT_TIMESTAMP)
        ON CONFLICT(subject_id) DO UPDATE SET
          limit_prompted=1,
          updated_at=CURRENT_TIMESTAMP
    """).bind(subject_id).run()


async def _total_absences(db, uid, subject_id):
    row = await db.prepare("SELECT COALESCE(SUM(absence_count),0) total FROM subject_absences WHERE user_id=? AND subject_id=?").bind(uid, subject_id).first()
    return int(_row(row, "total", 0) or 0)


async def _attendance_report(db, uid, subject_id=None):
    if subject_id is not None:
        subject = await _subject_by_id(db, uid, subject_id)
        if not subject:
            return "Não achei essa matéria."
        total = await _total_absences(db, uid, subject_id)
        settings = await _settings(db, subject_id)
        limit_value = _row(settings, "absence_limit") if settings else None
        if limit_value is None:
            return f"📊 {_row(subject,'name')}\n• Faltas: {total}\n• Limite: não informado"
        remaining = max(0, int(limit_value) - total)
        pct = (total / int(limit_value) * 100) if int(limit_value) > 0 else 0
        return (
            f"📊 {_row(subject,'name')}\n"
            f"• Faltas: {total}/{int(limit_value)}\n"
            f"• Restam: {remaining}\n"
            f"• Uso do limite: {pct:.0f}%"
        )

    subjects = await _rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    if not subjects:
        return "📊 Nenhuma matéria ativa cadastrada."
    out = ["📊 Faltas por matéria"]
    for subject in subjects:
        sid = int(_row(subject, "id"))
        total = await _total_absences(db, uid, sid)
        settings = await _settings(db, sid)
        limit_value = _row(settings, "absence_limit") if settings else None
        if limit_value is None:
            out.append(f"• {_row(subject,'name')}: {total} falta(s) — limite não informado")
        else:
            out.append(f"• {_row(subject,'name')}: {total}/{int(limit_value)} falta(s)")
    return "\n".join(out)


async def _record_absence(db, uid, session_id, class_date):
    session = await db.prepare("""
        SELECT ss.id,ss.subject_id,ss.start_time,ss.end_time,s.name
        FROM subject_sessions ss JOIN subjects s ON s.id=ss.subject_id
        WHERE ss.id=? AND s.user_id=? AND s.active=1
    """).bind(session_id, uid).first()
    if not session:
        return None, False

    units = _absence_units(_row(session, "start_time"), _row(session, "end_time"))
    existing = await db.prepare("SELECT id FROM subject_absences WHERE user_id=? AND session_id=? AND class_date=?").bind(uid, session_id, class_date).first()
    if existing:
        return session, False

    await db.prepare("""
        INSERT INTO subject_absences(user_id,subject_id,session_id,class_date,absence_count,start_time,end_time)
        VALUES(?,?,?,?,?,?,?)
    """).bind(
        uid,
        _row(session, "subject_id"),
        session_id,
        class_date,
        units,
        _row(session, "start_time"),
        _row(session, "end_time"),
    ).run()
    return session, True


async def handle_callback(db, token, callback):
    data = callback.get("data") or ""
    if not data.startswith("att:"):
        return False

    chat_id = ((callback.get("message") or {}).get("chat") or {}).get("id")
    if chat_id is None:
        return True
    uid = await _uid(db, int(chat_id))
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
        await send_message(token, chat_id, f"✅ Fechado. {_row(session,'name')}: presença moral registrada só na sua consciência. Eu não salvo o ‘vou’.")
        return True

    if action != "skip":
        await answer_callback(token, callback.get("id"), "Ação inválida.")
        return True

    session, created = await _record_absence(db, uid, session_id, class_date)
    if not session:
        await answer_callback(token, callback.get("id"), "Não consegui registrar.")
        return True

    units = _absence_units(_row(session, "start_time"), _row(session, "end_time"))
    await answer_callback(token, callback.get("id"), "Falta registrada.")
    total = await _total_absences(db, uid, int(_row(session, "subject_id")))
    if created:
        msg = f"❌ Falta registrada em {_row(session,'name')}: +{units}. Total agora: {total}."
    else:
        msg = f"Essa falta de {_row(session,'name')} já estava registrada. Total: {total}."
    await send_message(token, chat_id, msg)

    settings = await _settings(db, int(_row(session, "subject_id")))
    prompted = int(_row(settings, "limit_prompted", 0) or 0) if settings else 0
    if not prompted:
        await app.set_state(db, uid, "attendance_limit_first", {"subject_id": int(_row(session, "subject_id")), "subject_name": _row(session, "name")})
        await send_message(
            token,
            chat_id,
            f"Qual é o seu limite de faltas em {_row(session,'name')}?\n"
            "Manda só o número. Se não quiser informar agora, diga `não vou informar`.",
            reply_markup=_kb([["Não vou informar"], ["❌ Cancelar ação"]]),
        )
    return True


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    uid = await _uid(db, int(chat_id))
    if uid is None:
        return False

    text = (message.get("text") or "").strip()
    n = _norm(text)
    state, payload = await app.get_state(db, uid)

    if state == "attendance_limit_first":
        sid = int(payload.get("subject_id"))
        if n in {"nao vou informar", "nao informar", "agora nao", "depois"}:
            await _mark_prompted_without_limit(db, sid)
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Beleza. Não vou ficar perguntando toda vez. Você pode informar depois em Matérias → Limite de faltas.", reply_markup=_kb(ATTENDANCE_KB))
            return True
        if n in {"cancelar", "cancelar acao"}:
            await _mark_prompted_without_limit(db, sid)
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Certo. Limite deixado em aberto.", reply_markup=_kb(ATTENDANCE_KB))
            return True
        if not re.fullmatch(r"\d{1,3}", n):
            await send_message(token, chat_id, "Manda só o número do limite, ou `não vou informar`.")
            return True
        value = int(n)
        await _set_limit(db, sid, value)
        await app.clear_state(db, uid)
        total = await _total_absences(db, uid, sid)
        await send_message(token, chat_id, f"✅ Limite salvo: {value}. Você está com {total}/{value} falta(s).", reply_markup=_kb(ATTENDANCE_KB))
        return True

    if state == "attendance_limit_subject":
        subject, _ = await _subject_by_text(db, uid, text)
        if not subject:
            await send_message(token, chat_id, "Não achei essa matéria. Escolha uma da lista.", reply_markup=_kb(await _subject_keyboard(db, uid)))
            return True
        await app.set_state(db, uid, "attendance_limit_value", {"subject_id": int(_row(subject, "id")), "subject_name": _row(subject, "name")})
        await send_message(token, chat_id, f"Qual é o limite de faltas em {_row(subject,'name')}? Manda só o número.", reply_markup=_kb([["❌ Cancelar ação"]]))
        return True

    if state == "attendance_limit_value":
        if n in {"cancelar", "cancelar acao"}:
            await app.clear_state(db, uid)
            await send_message(token, chat_id, "Cancelado.", reply_markup=_kb(ATTENDANCE_KB))
            return True
        if not re.fullmatch(r"\d{1,3}", n):
            await send_message(token, chat_id, "Manda só o número do limite.")
            return True
        sid = int(payload.get("subject_id"))
        value = int(n)
        await _set_limit(db, sid, value)
        await app.clear_state(db, uid)
        total = await _total_absences(db, uid, sid)
        await send_message(token, chat_id, f"✅ Limite de {_row(payload,'subject_name',payload.get('subject_name')) or payload.get('subject_name')} salvo: {total}/{value} falta(s).", reply_markup=_kb(ATTENDANCE_KB))
        return True

    if state == "attendance_report_subject":
        subject, _ = await _subject_by_text(db, uid, text)
        if not subject:
            await send_message(token, chat_id, "Não achei essa matéria. Escolha uma da lista.", reply_markup=_kb(await _subject_keyboard(db, uid)))
            return True
        await app.clear_state(db, uid)
        await send_message(token, chat_id, await _attendance_report(db, uid, int(_row(subject, "id"))), reply_markup=_kb(ATTENDANCE_KB))
        return True

    if n in {"faltas", "minhas faltas", "ver faltas", "quantas faltas tenho", "contabilizacao de faltas"} or text == "📊 Ver faltas":
        await send_message(token, chat_id, await _attendance_report(db, uid), reply_markup=_kb(ATTENDANCE_KB))
        return True

    if text == "⚙️ Limite de faltas" or n in {"informar limite de faltas", "definir limite de faltas", "limite de faltas"}:
        await app.set_state(db, uid, "attendance_limit_subject", {})
        await send_message(token, chat_id, "De qual matéria você quer informar o limite de faltas?", reply_markup=_kb(await _subject_keyboard(db, uid)))
        return True

    m = re.search(r"(?:quantas|quanto).*faltas.*(?:em|de)\s+(.+)$", n)
    if m:
        subject, _ = await _subject_by_text(db, uid, m.group(1))
        if subject:
            await send_message(token, chat_id, await _attendance_report(db, uid, int(_row(subject, "id"))), reply_markup=_kb(ATTENDANCE_KB))
            return True

    m = re.search(r"(?:limite de faltas|faltas maximas).*?(?:em|de)\s+(.+?)\s+(?:e|eh|=)?\s*(\d{1,3})$", n)
    if m:
        subject, _ = await _subject_by_text(db, uid, m.group(1))
        if subject:
            value = int(m.group(2))
            await _set_limit(db, int(_row(subject, "id")), value)
            await send_message(token, chat_id, f"✅ Limite de {_row(subject,'name')} salvo: {value} falta(s).", reply_markup=_kb(ATTENDANCE_KB))
            return True

    return False


async def dispatch_class_attendance(db, token):
    now = _now()
    weekday = app.WEEKDAY_NAMES[now.weekday()]
    today = now.date().isoformat()
    sessions = await _rows(db.prepare("""
        SELECT ss.id,ss.start_time,ss.end_time,ss.location,s.name,u.id user_id,u.telegram_chat_id
        FROM subject_sessions ss
        JOIN subjects s ON s.id=ss.subject_id
        JOIN users u ON u.id=s.user_id
        WHERE s.active=1 AND ss.weekday=?
    """).bind(weekday))

    for session in sessions:
        if _row(session, "start_time") != now.strftime("%H:%M"):
            continue
        uid = int(_row(session, "user_id"))
        key = f"attendance:{today}:{_row(session,'id')}"
        sent = await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid, key).first()
        if sent:
            continue
        chat_id = int(_row(session, "telegram_chat_id"))
        await send_message(
            token,
            chat_id,
            f"🎓 Aula agora: {_row(session,'name')} — {_row(session,'start_time')}–{_row(session,'end_time')}"
            + (f" ({_row(session,'location')})" if _row(session, "location") else "")
            + "\nVocê vai?",
            reply_markup=_inline(int(_row(session, "id")), today),
        )
        await db.prepare("INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid, key).run()


def install():
    attendance_row = ["📊 Ver faltas", "⚙️ Limite de faltas"]
    try:
        if attendance_row not in app.ACADEMIC_KB:
            app.ACADEMIC_KB.insert(-1, attendance_row)
    except Exception:
        pass

    try:
        import academic_intelligence
        if attendance_row not in academic_intelligence.ACADEMIC_KB:
            academic_intelligence.ACADEMIC_KB.insert(-1, attendance_row)
    except Exception:
        pass
