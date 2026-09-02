import re
import unicodedata
from datetime import datetime, timedelta, timezone

import academic_intelligence
import app
import runtime_guard
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
ACADEMIC_KB = [
    ["📚 Minhas matérias", "⚙️ Gerenciar matérias"],
    ["📝 Adicionar prova", "📋 Provas"],
    ["✏️ Editar prova", "🚫 Cancelar prova"],
    ["📥 Importar grade por PDF/texto"],
    ["🏠 Menu principal"],
]
CANCEL_KB = [["❌ Cancelar ação"]]
EDIT_KB = [
    ["🏷️ Nome", "📚 Matéria"],
    ["📅 Data", "⏰ Horário"],
    ["⬅️ Voltar às provas", "❌ Cancelar ação"],
]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9#:/ ]+", " ", value)
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


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


async def _future_exams(db, uid):
    today = datetime.now(timezone.utc).astimezone(LOCAL_TZ).date().isoformat()
    return await _rows(db.prepare("""
        SELECT di.id,di.title,di.due_date,di.due_time,di.details,s.name subject,s.id subject_id
        FROM daily_items di
        LEFT JOIN subjects s ON di.details='exam:'||s.id
        WHERE di.user_id=? AND di.status='pendente'
          AND di.details LIKE 'exam:%' AND di.due_date>=?
        ORDER BY di.due_date,COALESCE(di.due_time,'99:99'),di.id
    """).bind(uid,today))


async def _exam_by_id(db, uid, exam_id):
    return await db.prepare("""
        SELECT di.id,di.title,di.due_date,di.due_time,di.details,s.name subject,s.id subject_id
        FROM daily_items di
        LEFT JOIN subjects s ON di.details='exam:'||s.id
        WHERE di.id=? AND di.user_id=? AND di.status='pendente' AND di.details LIKE 'exam:%'
        LIMIT 1
    """).bind(int(exam_id), uid).first()


async def _resolve_exam(db, uid, text):
    exams = await _future_exams(db, uid)
    n = _norm(text)
    m = re.search(r"#(\d+)", text or "")
    if m:
        iid = int(m.group(1))
        matches = [e for e in exams if int(_row(e, "id")) == iid]
        return (matches[0] if len(matches) == 1 else None), exams

    cleaned = re.sub(
        r"^(?:butler\s+)?(?:(?:cancela|cancelar|cancele|remove|remover|apaga|apagar|edita|editar|edite|altera|alterar)\s+)?(?:a\s+)?prova\s+(?:de|da|do)?\s*",
        "",
        n,
    ).strip()
    if cleaned:
        matches = []
        for e in exams:
            hay = _norm((_row(e, "subject") or "") + " " + (_row(e, "title") or ""))
            if cleaned in hay or hay in cleaned:
                matches.append(e)
            elif any(tok in hay for tok in cleaned.split() if len(tok) >= 3):
                matches.append(e)
        unique = []
        seen = set()
        for e in matches:
            iid = int(_row(e, "id"))
            if iid not in seen:
                seen.add(iid)
                unique.append(e)
        if len(unique) == 1:
            return unique[0], exams
    if len(exams) == 1:
        return exams[0], exams
    return None, exams


async def _cancel_exam(db, uid, exam):
    await db.prepare(
        "UPDATE daily_items SET status='cancelado',cancelled_at=CURRENT_TIMESTAMP "
        "WHERE id=? AND user_id=? AND details LIKE 'exam:%'"
    ).bind(int(_row(exam, "id")), uid).run()


async def _reset_schedule_notifications(db, uid, exam_id):
    await db.prepare(
        "DELETE FROM notification_log WHERE user_id=? AND notification_key LIKE ?"
    ).bind(uid, f"exam:{int(exam_id)}:%").run()


async def _exam_list_text(db, uid):
    exams = await _future_exams(db, uid)
    if not exams:
        return "📝 Nenhuma prova futura cadastrada."
    lines = ["📝 Próximas provas"]
    for exam in exams:
        when = f"{_row(exam,'due_date')[8:10]}/{_row(exam,'due_date')[5:7]}"
        if _row(exam, "due_time"):
            when += f" às {_row(exam,'due_time')}"
        title = _row(exam, "title") or (_row(exam, "subject") or "Prova")
        subject = _row(exam, "subject")
        default_title = f"Prova de {subject}" if subject else None
        label = title if not subject or title == default_title else f"{title} — {subject}"
        lines.append(f"• #{_row(exam,'id')} {label} — {when}")
    lines.append("\nUse ✏️ Editar prova para alterar nome, matéria, data ou horário.")
    return "\n".join(lines)


async def _show_edit_menu(db, token, chat, uid, exam_id):
    exam = await _exam_by_id(db, uid, exam_id)
    if not exam:
        await runtime_guard._clear(db, uid)
        await send_message(token, int(chat), "Não encontrei essa prova ativa.", reply_markup=_kb(ACADEMIC_KB))
        return True
    await runtime_guard._set_state(db, uid, "ai_edit_exam_menu", {"exam_id": int(exam_id)})
    when = f"{_row(exam,'due_date')[8:10]}/{_row(exam,'due_date')[5:7]}"
    if _row(exam, "due_time"):
        when += f" às {_row(exam,'due_time')}"
    text = (
        f"✏️ Editando #{_row(exam,'id')}\n"
        f"Nome: {_row(exam,'title')}\n"
        f"Matéria: {_row(exam,'subject') or 'não identificada'}\n"
        f"Quando: {when}\n\n"
        "O que você quer alterar?"
    )
    await send_message(token, int(chat), text, reply_markup=_kb(EDIT_KB))
    return True


async def _start_edit(db, token, chat, uid):
    exams = await _future_exams(db, uid)
    if not exams:
        await send_message(token, int(chat), "Não há prova futura para editar.", reply_markup=_kb(ACADEMIC_KB))
        return True
    await runtime_guard._set_state(db, uid, "ai_edit_exam_select", {})
    lines = ["Qual prova você quer editar?"]
    for exam in exams:
        when = f"{_row(exam,'due_date')[8:10]}/{_row(exam,'due_date')[5:7]}"
        if _row(exam, "due_time"):
            when += f" {_row(exam,'due_time')}"
        lines.append(f"• #{_row(exam,'id')} {_row(exam,'title')} — {when}")
    await send_message(token, int(chat), "\n".join(lines), reply_markup=_kb(CANCEL_KB))
    return True


async def handle_message(db, token, message):
    chat = (message.get("chat") or {}).get("id")
    if chat is None:
        return False
    uid = await _uid(db, int(chat))
    if not uid:
        return False
    text = (message.get("text") or "").strip()
    n = _norm(text)
    state, payload = await runtime_guard._state(db, uid)

    exam_wizard_states = {
        "ai_exam_subject", "ai_exam_date", "ai_exam_time",
        "ai_edit_exam_select", "ai_edit_exam_menu", "ai_edit_exam_name",
        "ai_edit_exam_subject", "ai_edit_exam_date", "ai_edit_exam_time",
    }
    if state in exam_wizard_states and (text == "❌ Cancelar ação" or n in ("cancelar", "cancela", "cancelar acao", "para", "parar", "desiste", "desisti")):
        await runtime_guard._clear(db, uid)
        await send_message(token, int(chat), "Operação de prova cancelada. Nada adicional foi alterado.", reply_markup=_kb(ACADEMIC_KB))
        return True

    if state == "ai_edit_exam_select":
        exam, _ = await _resolve_exam(db, uid, text)
        if not exam:
            await send_message(token, int(chat), "Não achei uma prova única. Use o nome ou o #ID mostrado na lista.", reply_markup=_kb(CANCEL_KB))
            return True
        return await _show_edit_menu(db, token, chat, uid, int(_row(exam, "id")))

    if state == "ai_edit_exam_menu":
        exam_id = int(payload.get("exam_id"))
        if text == "🏷️ Nome":
            await runtime_guard._set_state(db, uid, "ai_edit_exam_name", {"exam_id": exam_id})
            await send_message(token, int(chat), "Qual será o novo nome da prova?", reply_markup=_kb(CANCEL_KB))
            return True
        if text == "📚 Matéria":
            subjects = await _rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
            await runtime_guard._set_state(db, uid, "ai_edit_exam_subject", {"exam_id": exam_id})
            await send_message(token, int(chat), "Qual é a matéria correta?\n\n" + "\n".join(f"• {_row(s,'name')}" for s in subjects), reply_markup=_kb(CANCEL_KB))
            return True
        if text == "📅 Data":
            await runtime_guard._set_state(db, uid, "ai_edit_exam_date", {"exam_id": exam_id})
            await send_message(token, int(chat), "Nova data? Ex.: `02/09`, `amanhã` ou `próxima terça`.", reply_markup=_kb(CANCEL_KB))
            return True
        if text == "⏰ Horário":
            await runtime_guard._set_state(db, uid, "ai_edit_exam_time", {"exam_id": exam_id})
            await send_message(token, int(chat), "Novo horário? Ex.: `14h`, `14:30` ou `sem horário`.", reply_markup=_kb(CANCEL_KB))
            return True
        if text == "⬅️ Voltar às provas":
            await runtime_guard._clear(db, uid)
            await send_message(token, int(chat), await _exam_list_text(db, uid), reply_markup=_kb(ACADEMIC_KB))
            return True
        await send_message(token, int(chat), "Escolha Nome, Matéria, Data ou Horário.", reply_markup=_kb(EDIT_KB))
        return True

    if state == "ai_edit_exam_name":
        exam_id = int(payload.get("exam_id"))
        title = " ".join(text.split()).strip()
        if not title or len(title) > 180:
            await send_message(token, int(chat), "Use um nome entre 1 e 180 caracteres.", reply_markup=_kb(CANCEL_KB))
            return True
        await db.prepare(
            "UPDATE daily_items SET title=? WHERE id=? AND user_id=? AND status='pendente' AND details LIKE 'exam:%'"
        ).bind(title, exam_id, uid).run()
        await send_message(token, int(chat), "✅ Nome da prova atualizado.")
        return await _show_edit_menu(db, token, chat, uid, exam_id)

    if state == "ai_edit_exam_subject":
        exam_id = int(payload.get("exam_id"))
        subject, _ = await academic_intelligence._subject_lookup(db, uid, text)
        if not subject:
            await send_message(token, int(chat), "Não achei uma matéria única com esse nome. Use o nome como aparece em Minhas matérias.", reply_markup=_kb(CANCEL_KB))
            return True
        exam = await _exam_by_id(db, uid, exam_id)
        if not exam:
            await runtime_guard._clear(db, uid)
            return True
        old_subject = _row(exam, "subject")
        current_title = _row(exam, "title") or ""
        old_default = f"Prova de {old_subject}" if old_subject else None
        new_default = f"Prova de {_row(subject,'name')}"
        new_title = new_default if old_default and current_title == old_default else current_title
        await db.prepare(
            "UPDATE daily_items SET details=?,title=? WHERE id=? AND user_id=? AND status='pendente' AND details LIKE 'exam:%'"
        ).bind(f"exam:{int(_row(subject,'id'))}", new_title, exam_id, uid).run()
        await send_message(token, int(chat), "✅ Matéria da prova atualizada.")
        return await _show_edit_menu(db, token, chat, uid, exam_id)

    if state == "ai_edit_exam_date":
        exam_id = int(payload.get("exam_id"))
        today = academic_intelligence._now().date()
        due = academic_intelligence._date_from_phrase(text, today)
        if not due or due < today:
            await send_message(token, int(chat), "Não reconheci uma data válida de hoje em diante.", reply_markup=_kb(CANCEL_KB))
            return True
        await db.prepare(
            "UPDATE daily_items SET due_date=? WHERE id=? AND user_id=? AND status='pendente' AND details LIKE 'exam:%'"
        ).bind(due.isoformat(), exam_id, uid).run()
        await _reset_schedule_notifications(db, uid, exam_id)
        await send_message(token, int(chat), f"✅ Data atualizada para {due.strftime('%d/%m')}.")
        return await _show_edit_menu(db, token, chat, uid, exam_id)

    if state == "ai_edit_exam_time":
        exam_id = int(payload.get("exam_id"))
        no_time = n in ("sem horario", "sem hora", "nao sei", "remover horario", "tirar horario")
        tm = None if no_time else app.parse_time(text)
        if tm is None and not no_time:
            await send_message(token, int(chat), "Manda `14h`, `14:30` ou `sem horário`.", reply_markup=_kb(CANCEL_KB))
            return True
        await db.prepare(
            "UPDATE daily_items SET due_time=? WHERE id=? AND user_id=? AND status='pendente' AND details LIKE 'exam:%'"
        ).bind(tm, exam_id, uid).run()
        await _reset_schedule_notifications(db, uid, exam_id)
        await send_message(token, int(chat), "✅ Horário atualizado" + (f" para {tm}." if tm else "; a prova ficou sem horário definido."))
        return await _show_edit_menu(db, token, chat, uid, exam_id)

    if state == "ai_cancel_exam":
        if text == "❌ Cancelar ação" or n in ("cancelar", "cancela", "cancelar acao", "voltar"):
            await runtime_guard._clear(db, uid)
            await send_message(token, int(chat), "Cancelamento de prova abortado.", reply_markup=_kb(ACADEMIC_KB))
            return True
        exam, _ = await _resolve_exam(db, uid, text)
        if not exam:
            await send_message(token, int(chat), "Não achei uma prova única. Manda o nome da matéria ou o #ID da lista.", reply_markup=_kb(CANCEL_KB))
            return True
        await _cancel_exam(db, uid, exam)
        await runtime_guard._clear(db, uid)
        await send_message(token, int(chat), f"🚫 {_row(exam,'title')} cancelada.", reply_markup=_kb(ACADEMIC_KB))
        return True

    if text == "✏️ Editar prova":
        return await _start_edit(db, token, chat, uid)

    if text == "🚫 Cancelar prova":
        exams = await _future_exams(db, uid)
        if not exams:
            await send_message(token, int(chat), "Não há prova futura para cancelar.", reply_markup=_kb(ACADEMIC_KB))
            return True
        await runtime_guard._set_state(db, uid, "ai_cancel_exam", {})
        lines = ["Qual prova você quer cancelar?"]
        for e in exams:
            when = f"{_row(e,'due_date')[8:10]}/{_row(e,'due_date')[5:7]}" + (f" {_row(e,'due_time')}" if _row(e,'due_time') else "")
            lines.append(f"• #{_row(e,'id')} {_row(e,'title')} — {when}")
        await send_message(token, int(chat), "\n".join(lines), reply_markup=_kb(CANCEL_KB))
        return True

    # Linguagem natural: editar/alterar prova.
    if "prova" in n and re.search(r"\b(edita|editar|edite|altera|alterar|muda|mudar)\b", n):
        exam, exams = await _resolve_exam(db, uid, text)
        if exam:
            return await _show_edit_menu(db, token, chat, uid, int(_row(exam, "id")))
        if not exams:
            await send_message(token, int(chat), "Não achei nenhuma prova futura para editar.", reply_markup=_kb(ACADEMIC_KB))
            return True
        return await _start_edit(db, token, chat, uid)

    # Linguagem natural: cancela/remove/apaga a prova de X.
    if "prova" in n and re.search(r"\b(cancela|cancelar|cancele|remove|remover|apaga|apagar)\b", n):
        exam, exams = await _resolve_exam(db, uid, text)
        if exam:
            await _cancel_exam(db, uid, exam)
            await send_message(token, int(chat), f"🚫 {_row(exam,'title')} cancelada.", reply_markup=_kb(ACADEMIC_KB))
            return True
        if not exams:
            await send_message(token, int(chat), "Não achei nenhuma prova futura para cancelar.", reply_markup=_kb(ACADEMIC_KB))
            return True
        await runtime_guard._set_state(db, uid, "ai_cancel_exam", {})
        await send_message(token, int(chat), "Achei mais de uma possibilidade. Qual prova exatamente? Use o nome ou o #ID em 📋 Provas.", reply_markup=_kb(CANCEL_KB))
        return True

    return False


def install():
    academic_intelligence.ACADEMIC_KB = ACADEMIC_KB
    academic_intelligence._exam_list = _exam_list_text
    app.ACADEMIC_KB = ACADEMIC_KB
