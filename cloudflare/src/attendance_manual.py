import re
import unicodedata
from datetime import date, timedelta

import app
import attendance_management
import attendance_patch as attendance
from attendance_enhancement import ensure_schema
from telegram_api import send_message

MANUAL_ROW = ["❌ Registrar falta", "✅ Registrar presença"]
CANCEL_KB = [["❌ Cancelar ação"]]
DAY_NAMES = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9/ ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _row(row, key, default=None):
    return attendance._row(row, key, default)


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _ensure_manual_schema(db):
    await ensure_schema(db)
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS subject_presences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            class_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, session_id, class_date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY(session_id) REFERENCES subject_sessions(id) ON DELETE CASCADE
        )
    """).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_presences_user_subject ON subject_presences(user_id, subject_id, class_date)"
    ).run()


def _parse_date(text, today):
    n = _norm(text)
    if "ontem" in n:
        return today - timedelta(days=1)
    if "hoje" in n:
        return today
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", n)
    if not m:
        return today
    day = int(m.group(1)); month = int(m.group(2))
    year = int(m.group(3)) if m.group(3) else today.year
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


async def _subject_keyboard(db, uid):
    return await attendance._subject_keyboard(db, uid)


async def _sessions_for_date(db, uid, subject_id, target):
    rows = await attendance._rows(db.prepare("""
        SELECT ss.id,ss.subject_id,ss.weekday,ss.start_time,ss.end_time,s.name
        FROM subject_sessions ss
        JOIN subjects s ON s.id=ss.subject_id
        WHERE ss.subject_id=? AND s.user_id=? AND s.active=1
        ORDER BY ss.start_time
    """).bind(subject_id, uid))
    wanted = _norm(DAY_NAMES[target.weekday()])
    short = wanted.replace(" feira", "")
    return [
        r for r in rows
        if _norm(_row(r, "weekday")) in {wanted, short}
    ]


def _format_date(target):
    return target.strftime("%d/%m/%Y")


async def _apply(db, token, chat_id, uid, session, target, kind):
    await _ensure_manual_schema(db)
    session_id = int(_row(session, "id"))
    subject_id = int(_row(session, "subject_id"))
    name = _row(session, "name")
    class_date = target.isoformat()
    units = attendance._absence_units(_row(session, "start_time"), _row(session, "end_time"))

    if kind == "presence":
        old = await db.prepare(
            "SELECT id,absence_count FROM subject_absences WHERE user_id=? AND session_id=? AND class_date=?"
        ).bind(uid, session_id, class_date).first()
        if old:
            await db.prepare(
                "DELETE FROM subject_absences WHERE user_id=? AND session_id=? AND class_date=?"
            ).bind(uid, session_id, class_date).run()
        existing = await db.prepare(
            "SELECT id FROM subject_presences WHERE user_id=? AND session_id=? AND class_date=?"
        ).bind(uid, session_id, class_date).first()
        if not existing:
            await db.prepare("""
                INSERT INTO subject_presences(user_id,subject_id,session_id,class_date)
                VALUES(?,?,?,?)
            """).bind(uid, subject_id, session_id, class_date).run()
        total = await attendance._total_absences(db, uid, subject_id)
        correction = ""
        if old:
            removed = int(_row(old, "absence_count", units) or units)
            correction = f" Corrigi a falta anterior e retirei {removed} do total."
        elif existing:
            correction = " Essa presença já estava registrada; não dupliquei."
        await send_message(
            token, chat_id,
            f"✅ Presença registrada em {name} — {_format_date(target)}, {_row(session,'start_time')}–{_row(session,'end_time')}.{correction} Faltas na matéria: {total}.",
            reply_markup=_kb(attendance_management.MANAGE_ATTENDANCE_KB),
        )
        return

    await db.prepare(
        "DELETE FROM subject_presences WHERE user_id=? AND session_id=? AND class_date=?"
    ).bind(uid, session_id, class_date).run()
    _, created = await attendance._record_absence(db, uid, session_id, class_date)
    total = await attendance._total_absences(db, uid, subject_id)
    if created:
        msg = f"❌ Falta registrada em {name} — {_format_date(target)}: +{units}. Total agora: {total}."
    else:
        msg = f"Essa falta de {name} em {_format_date(target)} já estava registrada. Total: {total}."
    await send_message(token, chat_id, msg, reply_markup=_kb(attendance_management.MANAGE_ATTENDANCE_KB))


async def _select_or_apply(db, token, chat_id, uid, subject, target, kind):
    sessions = await _sessions_for_date(db, uid, int(_row(subject, "id")), target)
    if not sessions:
        await app.clear_state(db, uid)
        await send_message(
            token, chat_id,
            f"Não achei aula cadastrada de {_row(subject,'name')} em {_format_date(target)}. Não vou inventar presença nem falta para um horário que não existe na grade.",
            reply_markup=_kb(attendance_management.MANAGE_ATTENDANCE_KB),
        )
        return True
    if len(sessions) == 1:
        await app.clear_state(db, uid)
        await _apply(db, token, chat_id, uid, sessions[0], target, kind)
        return True

    ids = [int(_row(s, "id")) for s in sessions]
    await app.set_state(db, uid, "attendance_manual_session", {
        "kind": kind,
        "date": target.isoformat(),
        "session_ids": ids,
    })
    lines = [f"Há mais de uma aula de {_row(subject,'name')} em {_format_date(target)}. Qual delas?"]
    for i, session in enumerate(sessions, 1):
        lines.append(f"{i}. {_row(session,'start_time')}–{_row(session,'end_time')}")
    buttons = [[str(i)] for i in range(1, len(sessions) + 1)] + CANCEL_KB
    await send_message(token, chat_id, "\n".join(lines), reply_markup=_kb(buttons))
    return True


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    uid = await attendance._uid(db, int(chat_id))
    if uid is None:
        return False

    text = (message.get("text") or "").strip()
    n = _norm(text)
    state, payload = await app.get_state(db, uid)

    if state and state.startswith("attendance_manual_") and (text == "❌ Cancelar ação" or n in {"cancelar", "cancelar acao", "voltar"}):
        await app.clear_state(db, uid)
        await send_message(token, chat_id, "Registro de frequência cancelado. Nada foi alterado.", reply_markup=_kb(attendance_management.MANAGE_ATTENDANCE_KB))
        return True

    if state == "attendance_manual_subject":
        subject, _ = await attendance._subject_by_text(db, uid, text)
        if not subject:
            await send_message(token, chat_id, "Não achei essa matéria. Escolha uma da lista.", reply_markup=_kb(await _subject_keyboard(db, uid)))
            return True
        payload["subject_id"] = int(_row(subject, "id"))
        payload["subject_name"] = _row(subject, "name")
        await app.set_state(db, uid, "attendance_manual_date", payload)
        action = "a presença" if payload.get("kind") == "presence" else "a falta"
        await send_message(token, chat_id, f"Para qual dia registro {action} em {_row(subject,'name')}?", reply_markup=_kb([["Hoje", "Ontem"], ["❌ Cancelar ação"]]))
        return True

    if state == "attendance_manual_date":
        target = _parse_date(text, attendance._now().date())
        if target is None:
            await send_message(token, chat_id, "Não reconheci essa data. Use `Hoje`, `Ontem` ou `dd/mm`.")
            return True
        subject = await attendance._subject_by_id(db, uid, int(payload.get("subject_id")))
        if not subject:
            await app.clear_state(db, uid)
            return True
        return await _select_or_apply(db, token, chat_id, uid, subject, target, payload.get("kind"))

    if state == "attendance_manual_session":
        if not re.fullmatch(r"\d{1,2}", n):
            await send_message(token, chat_id, "Escolha o número da aula ou cancele.")
            return True
        idx = int(n) - 1
        ids = payload.get("session_ids") or []
        if idx < 0 or idx >= len(ids):
            await send_message(token, chat_id, "Esse número não está na lista.")
            return True
        session = await db.prepare("""
            SELECT ss.id,ss.subject_id,ss.start_time,ss.end_time,s.name
            FROM subject_sessions ss JOIN subjects s ON s.id=ss.subject_id
            WHERE ss.id=? AND s.user_id=?
        """).bind(ids[idx], uid).first()
        target = date.fromisoformat(payload.get("date"))
        await app.clear_state(db, uid)
        if session:
            await _apply(db, token, chat_id, uid, session, target, payload.get("kind"))
        return True

    if text in MANUAL_ROW:
        kind = "presence" if text == "✅ Registrar presença" else "absence"
        await app.set_state(db, uid, "attendance_manual_subject", {"kind": kind})
        action = "presença" if kind == "presence" else "falta"
        await send_message(token, chat_id, f"Em qual matéria você quer registrar {action}?", reply_markup=_kb(await _subject_keyboard(db, uid)))
        return True

    presence_signal = any(x in n for x in (
        "estou presente", "to presente", "tô presente", "compareci", "fui pra aula", "fui para aula", "fui na aula"
    ))
    absence_signal = any(x in n for x in (
        "faltei", "nao fui pra aula", "nao fui para aula", "nao fui na aula", "perdi a aula"
    ))
    if not presence_signal and not absence_signal:
        return False

    kind = "presence" if presence_signal else "absence"
    target = _parse_date(text, attendance._now().date())
    if target is None:
        await send_message(token, chat_id, "Entendi o registro de frequência, mas a data não ficou válida. Use `hoje`, `ontem` ou `dd/mm`.")
        return True
    subject, _ = await attendance._subject_by_text(db, uid, text)
    if not subject:
        await app.set_state(db, uid, "attendance_manual_subject", {"kind": kind, "date": target.isoformat()})
        action = "presença" if kind == "presence" else "falta"
        await send_message(token, chat_id, f"Entendi que você quer registrar {action}. Em qual matéria?", reply_markup=_kb(await _subject_keyboard(db, uid)))
        return True
    return await _select_or_apply(db, token, chat_id, uid, subject, target, kind)


def install():
    if MANUAL_ROW not in attendance_management.MANAGE_ATTENDANCE_KB:
        attendance_management.MANAGE_ATTENDANCE_KB.insert(0, MANUAL_ROW)
    if MANUAL_ROW not in app.ACADEMIC_KB:
        app.ACADEMIC_KB.insert(-1, MANUAL_ROW)

    original = app.handle_message

    async def wrapped(db, token, message):
        if await handle_message(db, token, message):
            return True
        return await original(db, token, message)

    app.handle_message = wrapped
