from datetime import date
import re

import app
import quality_patch
import academic_intelligence


SIGAA_SCHEDULE_GUIDE = (
    "📚 Antes de importar suas matérias, use de preferência o painel principal do SIGAA onde aparece a tabela "
    "`Componente Curricular | Local | Horário` — exatamente aquela visão que mostra códigos como `35M45`, `24M23` ou `2T23`.\n\n"
    "✅ Formatos aceitos: PDF com texto pesquisável/selecionável ou arquivo `.txt`.\n"
    "⭐ Recomendado: abrir essa grade no SIGAA e usar Imprimir → Salvar como PDF, confirmando que o texto continua selecionável.\n"
    "📝 O arquivo precisa preservar nome da matéria, local e o código de horário do SIGAA.\n"
    "🚫 Print, foto, imagem ou PDF escaneado não entram direto: o Butler não faz OCR em produção.\n\n"
    "Depois, vá em 📚 Matérias → 📥 Importar grade por PDF/texto. Antes de salvar, eu mostro o que entendi para você conferir."
)

IMPORT_SCHEDULE_PROMPT = (
    "📥 Envie sua grade em PDF com texto pesquisável/selecionável ou em `.txt`.\n\n"
    "⭐ Modelo recomendado: a tabela do painel principal do SIGAA com `Componente Curricular`, `Local` e `Horário`. "
    "O ideal é usar Imprimir → Salvar como PDF diretamente no navegador, e não tirar print.\n\n"
    "Eu preciso conseguir ler o nome da matéria, o local e códigos de horário como `35M45`, `24M23` ou `2T23`.\n"
    "🚫 Imagem, foto, print ou PDF escaneado não entram direto nesta versão."
)

SUBJECT_EDIT_KB = [
    ["✏️ Nome", "📅 Dia"],
    ["🕒 Horário", "📍 Sala/local"],
    ["➕ Adicionar aula", "🗑️ Remover aula"],
    ["✅ Finalizar edição", "❌ Cancelar ação"],
]

WEEKDAY_ALIASES = {
    "seg": "segunda-feira", "segunda": "segunda-feira", "segunda feira": "segunda-feira",
    "ter": "terça-feira", "terca": "terça-feira", "terça": "terça-feira", "terca feira": "terça-feira", "terça feira": "terça-feira",
    "qua": "quarta-feira", "quarta": "quarta-feira", "quarta feira": "quarta-feira",
    "qui": "quinta-feira", "quinta": "quinta-feira", "quinta feira": "quinta-feira",
    "sex": "sexta-feira", "sexta": "sexta-feira", "sexta feira": "sexta-feira",
    "sab": "sábado", "sabado": "sábado", "sábado": "sábado",
}


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


def _normalize_weekday(value):
    key = app.norm(value or "")
    return WEEKDAY_ALIASES.get(key)


def _parse_time_range(value):
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})\s*", value or "")
    if not match:
        return None
    sh, sm, eh, em = map(int, match.groups())
    if sh > 23 or eh > 23 or sm > 59 or em > 59:
        return None
    start = f"{sh:02d}:{sm:02d}"
    end = f"{eh:02d}:{em:02d}"
    if (eh, em) <= (sh, sm):
        return None
    return start, end


async def _subject_sessions(db, uid, sid):
    return await _rows(db.prepare(
        "SELECT ss.id,ss.weekday,ss.start_time,ss.end_time,ss.location "
        "FROM subject_sessions ss JOIN subjects s ON s.id=ss.subject_id "
        "WHERE s.user_id=? AND s.id=? ORDER BY ss.weekday,ss.start_time,ss.id"
    ).bind(uid, sid))


async def _subject_summary(db, uid, sid):
    subject = await db.prepare("SELECT name,active FROM subjects WHERE user_id=? AND id=?").bind(uid, sid).first()
    if not subject:
        return "Matéria não encontrada."
    sessions = await _subject_sessions(db, uid, sid)
    out = [f"✏️ Editando: {_row(subject, 'name')}"]
    if not sessions:
        out.append("\nNenhuma aula/horário cadastrado.")
    else:
        out.append("\nAulas cadastradas:")
        for pos, item in enumerate(sessions, 1):
            out.append(
                f"{pos}. {_row(item,'weekday').capitalize()} "
                f"{_row(item,'start_time')}–{_row(item,'end_time')} — "
                f"{_row(item,'location') or 'local não informado'}"
            )
    out.append("\nEscolha o que quer alterar.")
    return "\n".join(out)


async def _send_session_picker(db, token, chat, uid, sid, action):
    sessions = await _subject_sessions(db, uid, sid)
    if not sessions:
        await app.send(token, chat, "Essa matéria ainda não tem aulas cadastradas. Use ➕ Adicionar aula.", SUBJECT_EDIT_KB)
        return False
    lines = ["Qual aula você quer alterar? Responda com o número:"]
    for pos, item in enumerate(sessions, 1):
        lines.append(
            f"{pos}. {_row(item,'weekday').capitalize()} {_row(item,'start_time')}–{_row(item,'end_time')} — "
            f"{_row(item,'location') or 'local não informado'}"
        )
    await app.set_state(db, uid, "subject_edit_pick_session", {"sid": sid, "action": action})
    await app.send(token, chat, "\n".join(lines), app.CANCEL_KB)
    return True


async def _resolve_subject_selection(db, uid, text):
    subjects = await _rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? ORDER BY name").bind(uid))
    if text.isdigit():
        pos = int(text)
        if 1 <= pos <= len(subjects):
            return subjects[pos - 1]
    wanted = app.norm(text)
    for item in subjects:
        if app.norm(_row(item, "name")) == wanted:
            return item
    return None


def install():
    # Mantém o botão de encerrar rotina inclusive depois de confirmações parciais
    # tratadas pela quality_patch (ex.: "bebi água").
    quality_patch.ROUTINE_KB = academic_intelligence.ROUTINE_KB

    original_agenda = app.agenda_text
    original_handle_state = app.handle_state
    original_handle_message = app.handle_message

    async def agenda_with_exam_section(db, uid, target, include_overdue=False):
        # Pendência é relativa ao momento atual, não à data futura consultada.
        today = app.now_local().date() if hasattr(app, "now_local") else date.today()
        effective_overdue = bool(include_overdue and target <= today)

        base = await original_agenda(db, uid, target, effective_overdue)
        exams = await _rows(db.prepare(
            "SELECT id,title,due_time,status FROM daily_items "
            "WHERE user_id=? AND due_date=? AND status!='cancelado' AND details LIKE 'exam:%' "
            "ORDER BY COALESCE(due_time,'99:99'),id"
        ).bind(uid, target.isoformat()))
        if not exams:
            return base

        titles = {_row(r, "title") for r in exams}
        lines = []
        for line in base.splitlines():
            if any(title and title in line for title in titles):
                continue
            lines.append(line)

        lines = [line for line in lines if "Nada marcado. Um raro espaço em branco no calendário." not in line]
        lines.append("\n📝 Provas")
        for exam in exams:
            tm = f"{_row(exam,'due_time')} — " if _row(exam,'due_time') else ""
            status = " ✅" if _row(exam,"status") == "concluido" else ""
            lines.append(f"• 🧠 {tm}{_row(exam,'title')}{status}")
        lines.append("  E sim, eu vou lembrar antes. Descobrir a prova no próprio dia é uma tradição acadêmica que podemos dispensar. 😏")
        return "\n".join(lines)

    async def handle_state_with_academic_editing(db, token, chat, uid, owner, state, payload, message):
        text = (message.get("text") or "").strip()

        if state == "ask_name" and text and text not in ("❌ Cancelar ação", "/cancelar"):
            preferred_name = text[:60]
            await db.prepare("UPDATE users SET preferred_name=? WHERE id=?").bind(preferred_name, uid).run()
            await app.clear_state(db, uid)
            await app.send(token, chat, f"Fechado. Vou te chamar de {preferred_name}. Não abuse da intimidade.", app.MAIN_KB)
            await app.send(token, chat, SIGAA_SCHEDULE_GUIDE, app.MAIN_KB)
            return True

        if state == "subject_edit_select":
            if text in ("❌ Cancelar ação", "/cancelar"):
                await app.clear_state(db, uid)
                await app.send(token, chat, "Edição cancelada. Nada foi alterado.", app.MANAGE_SUBJECT_KB)
                return True
            subject = await _resolve_subject_selection(db, uid, text)
            if not subject:
                await app.send(token, chat, "Não achei essa matéria. Responda com o número da lista ou com o nome exato.", app.CANCEL_KB)
                return True
            sid = int(_row(subject, "id"))
            await app.set_state(db, uid, "subject_edit_menu", {"sid": sid})
            await app.send(token, chat, await _subject_summary(db, uid, sid), SUBJECT_EDIT_KB)
            return True

        if state == "subject_edit_menu":
            sid = int(payload.get("sid"))
            if text in ("❌ Cancelar ação", "/cancelar", "✅ Finalizar edição"):
                await app.clear_state(db, uid)
                await app.send(token, chat, "✅ Edição encerrada. Sua grade já está usando os dados atualizados.", app.ACADEMIC_KB)
                return True
            if text == "✏️ Nome":
                await app.set_state(db, uid, "subject_edit_name", {"sid": sid})
                await app.send(token, chat, "Qual será o novo nome da matéria?", app.CANCEL_KB)
                return True
            if text == "📅 Dia":
                return await _send_session_picker(db, token, chat, uid, sid, "day")
            if text == "🕒 Horário":
                return await _send_session_picker(db, token, chat, uid, sid, "time")
            if text == "📍 Sala/local":
                return await _send_session_picker(db, token, chat, uid, sid, "location")
            if text == "🗑️ Remover aula":
                return await _send_session_picker(db, token, chat, uid, sid, "remove")
            if text == "➕ Adicionar aula":
                await app.set_state(db, uid, "subject_edit_add_session", {"sid": sid})
                await app.send(
                    token, chat,
                    "Envie a nova aula assim:\n`segunda | 08:00-09:40 | PAV III, Sala 10`\n\nO local pode ficar vazio depois do último `|`.",
                    app.CANCEL_KB,
                )
                return True
            await app.send(token, chat, "Escolha uma das opções de edição abaixo.", SUBJECT_EDIT_KB)
            return True

        if state == "subject_edit_name":
            sid = int(payload.get("sid"))
            if text in ("❌ Cancelar ação", "/cancelar"):
                await app.set_state(db, uid, "subject_edit_menu", {"sid": sid})
                await app.send(token, chat, await _subject_summary(db, uid, sid), SUBJECT_EDIT_KB)
                return True
            new_name = text.strip()
            if len(new_name) < 2 or len(new_name) > 120:
                await app.send(token, chat, "Use um nome entre 2 e 120 caracteres.", app.CANCEL_KB)
                return True
            duplicate = await db.prepare(
                "SELECT id FROM subjects WHERE user_id=? AND lower(name)=lower(?) AND id<>? LIMIT 1"
            ).bind(uid, new_name, sid).first()
            if duplicate:
                await app.send(token, chat, "Você já tem outra matéria com esse nome. Escolha um nome diferente.", app.CANCEL_KB)
                return True
            await db.prepare("UPDATE subjects SET name=? WHERE user_id=? AND id=?").bind(new_name, uid, sid).run()
            await app.set_state(db, uid, "subject_edit_menu", {"sid": sid})
            await app.send(token, chat, await _subject_summary(db, uid, sid), SUBJECT_EDIT_KB)
            return True

        if state == "subject_edit_pick_session":
            sid = int(payload.get("sid"))
            if text in ("❌ Cancelar ação", "/cancelar"):
                await app.set_state(db, uid, "subject_edit_menu", {"sid": sid})
                await app.send(token, chat, await _subject_summary(db, uid, sid), SUBJECT_EDIT_KB)
                return True
            sessions = await _subject_sessions(db, uid, sid)
            if not text.isdigit() or not (1 <= int(text) <= len(sessions)):
                await app.send(token, chat, "Responda com o número de uma aula da lista.", app.CANCEL_KB)
                return True
            session = sessions[int(text) - 1]
            session_id = int(_row(session, "id"))
            action = payload.get("action")
            if action == "remove":
                await db.prepare(
                    "DELETE FROM subject_sessions WHERE id=? AND subject_id=? AND EXISTS(SELECT 1 FROM subjects WHERE id=? AND user_id=?)"
                ).bind(session_id, sid, sid, uid).run()
                await app.set_state(db, uid, "subject_edit_menu", {"sid": sid})
                await app.send(token, chat, await _subject_summary(db, uid, sid), SUBJECT_EDIT_KB)
                return True
            prompts = {
                "day": "Novo dia? Ex.: `segunda`, `qua`, `sexta`.",
                "time": "Novo horário? Ex.: `08:00-09:40`.",
                "location": "Nova sala/local? Ex.: `PAV III, Sala 10`.",
            }
            await app.set_state(db, uid, "subject_edit_session_value", {"sid": sid, "session_id": session_id, "action": action})
            await app.send(token, chat, prompts[action], app.CANCEL_KB)
            return True

        if state == "subject_edit_session_value":
            sid = int(payload.get("sid"))
            session_id = int(payload.get("session_id"))
            action = payload.get("action")
            if text in ("❌ Cancelar ação", "/cancelar"):
                await app.set_state(db, uid, "subject_edit_menu", {"sid": sid})
                await app.send(token, chat, await _subject_summary(db, uid, sid), SUBJECT_EDIT_KB)
                return True
            if action == "day":
                weekday = _normalize_weekday(text)
                if not weekday:
                    await app.send(token, chat, "Dia inválido. Use segunda/seg, terça/ter, quarta/qua, quinta/qui, sexta/sex ou sábado/sab.", app.CANCEL_KB)
                    return True
                await db.prepare(
                    "UPDATE subject_sessions SET weekday=? WHERE id=? AND subject_id=? AND EXISTS(SELECT 1 FROM subjects WHERE id=? AND user_id=?)"
                ).bind(weekday, session_id, sid, sid, uid).run()
            elif action == "time":
                parsed = _parse_time_range(text)
                if not parsed:
                    await app.send(token, chat, "Horário inválido. Use algo como `08:00-09:40`, com o fim depois do início.", app.CANCEL_KB)
                    return True
                await db.prepare(
                    "UPDATE subject_sessions SET start_time=?,end_time=? WHERE id=? AND subject_id=? AND EXISTS(SELECT 1 FROM subjects WHERE id=? AND user_id=?)"
                ).bind(parsed[0], parsed[1], session_id, sid, sid, uid).run()
            elif action == "location":
                if len(text) > 160:
                    await app.send(token, chat, "Local muito longo. Use até 160 caracteres.", app.CANCEL_KB)
                    return True
                await db.prepare(
                    "UPDATE subject_sessions SET location=? WHERE id=? AND subject_id=? AND EXISTS(SELECT 1 FROM subjects WHERE id=? AND user_id=?)"
                ).bind(text or None, session_id, sid, sid, uid).run()
            await app.set_state(db, uid, "subject_edit_menu", {"sid": sid})
            await app.send(token, chat, await _subject_summary(db, uid, sid), SUBJECT_EDIT_KB)
            return True

        if state == "subject_edit_add_session":
            sid = int(payload.get("sid"))
            if text in ("❌ Cancelar ação", "/cancelar"):
                await app.set_state(db, uid, "subject_edit_menu", {"sid": sid})
                await app.send(token, chat, await _subject_summary(db, uid, sid), SUBJECT_EDIT_KB)
                return True
            parts = [part.strip() for part in text.split("|", 2)]
            if len(parts) != 3:
                await app.send(token, chat, "Use o formato `segunda | 08:00-09:40 | PAV III, Sala 10`.", app.CANCEL_KB)
                return True
            weekday = _normalize_weekday(parts[0])
            times = _parse_time_range(parts[1])
            if not weekday or not times:
                await app.send(token, chat, "Não consegui validar o dia ou horário. Ex.: `segunda | 08:00-09:40 | Sala 10`.", app.CANCEL_KB)
                return True
            if len(parts[2]) > 160:
                await app.send(token, chat, "Local muito longo. Use até 160 caracteres.", app.CANCEL_KB)
                return True
            subject = await db.prepare("SELECT id FROM subjects WHERE user_id=? AND id=?").bind(uid, sid).first()
            if not subject:
                await app.clear_state(db, uid)
                await app.send(token, chat, "Essa matéria não existe mais.", app.ACADEMIC_KB)
                return True
            await db.prepare(
                "INSERT INTO subject_sessions(subject_id,weekday,start_time,end_time,location) VALUES(?,?,?,?,?)"
            ).bind(sid, weekday, times[0], times[1], parts[2] or None).run()
            await app.set_state(db, uid, "subject_edit_menu", {"sid": sid})
            await app.send(token, chat, await _subject_summary(db, uid, sid), SUBJECT_EDIT_KB)
            return True

        return await original_handle_state(db, token, chat, uid, owner, state, payload, message)

    async def handle_message_with_academic_tools(db, token, message):
        text = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        user = message.get("from") or {}
        chat_id = chat.get("id")

        if text == "📥 Importar grade por PDF/texto":
            if chat_id is None:
                return await original_handle_message(db, token, message)
            uid, _, _ = await app.ensure_user(db, int(chat_id), user)
            await app.set_state(db, uid, "import_schedule", {})
            await app.send(token, int(chat_id), IMPORT_SCHEDULE_PROMPT, app.CANCEL_KB)
            return

        if text == "✏️ Editar matéria":
            if chat_id is None:
                return await original_handle_message(db, token, message)
            uid, _, _ = await app.ensure_user(db, int(chat_id), user)
            subjects = await _rows(db.prepare("SELECT id,name,active FROM subjects WHERE user_id=? ORDER BY name").bind(uid))
            if not subjects:
                await app.send(token, int(chat_id), "Você ainda não tem matéria cadastrada para editar.", app.MANAGE_SUBJECT_KB)
                return
            lines = ["✏️ Qual matéria você quer editar? Responda com o número ou com o nome exato:"]
            for pos, subject in enumerate(subjects, 1):
                icon = "📘" if int(_row(subject, "active", 1)) else "🔒"
                lines.append(f"{pos}. {icon} {_row(subject,'name')}")
            await app.set_state(db, uid, "subject_edit_select", {})
            await app.send(token, int(chat_id), "\n".join(lines), app.CANCEL_KB)
            return

        return await original_handle_message(db, token, message)

    app.agenda_text = agenda_with_exam_section
    app.handle_state = handle_state_with_academic_editing
    app.handle_message = handle_message_with_academic_tools
