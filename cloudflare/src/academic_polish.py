from datetime import date

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


def install():
    # Mantém o botão de encerrar rotina inclusive depois de confirmações parciais
    # tratadas pela quality_patch (ex.: "bebi água").
    quality_patch.ROUTINE_KB = academic_intelligence.ROUTINE_KB

    original_agenda = app.agenda_text
    original_handle_state = app.handle_state
    original_handle_message = app.handle_message

    async def agenda_with_exam_section(db, uid, target, include_overdue=False):
        # Pendência é relativa ao momento atual, não à data futura consultada.
        # Se o usuário abre, por exemplo, a agenda da próxima segunda,
        # uma tarefa de amanhã ainda não venceu e não deve aparecer como atraso.
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
            # O app base vê prova como compromisso por compatibilidade do schema.
            # Remove essa linha para reapresentá-la na seção acadêmica correta.
            if any(title and title in line for title in titles):
                continue
            lines.append(line)

        # Se a única coisa do dia era prova, remove o texto de agenda vazia.
        lines = [line for line in lines if "Nada marcado. Um raro espaço em branco no calendário." not in line]
        lines.append("\n📝 Provas")
        for exam in exams:
            tm = f"{_row(exam,'due_time')} — " if _row(exam,'due_time') else ""
            status = " ✅" if _row(exam,"status") == "concluido" else ""
            lines.append(f"• 🧠 {tm}{_row(exam,'title')}{status}")
        lines.append("  E sim, eu vou lembrar antes. Descobrir a prova no próprio dia é uma tradição acadêmica que podemos dispensar. 😏")
        return "\n".join(lines)

    async def handle_state_with_first_access_guide(db, token, chat, uid, owner, state, payload, message):
        text = (message.get("text") or "").strip()
        if state == "ask_name" and text and text not in ("❌ Cancelar ação", "/cancelar"):
            preferred_name = text[:60]
            await db.prepare("UPDATE users SET preferred_name=? WHERE id=?").bind(preferred_name, uid).run()
            await app.clear_state(db, uid)
            await app.send(token, chat, f"Fechado. Vou te chamar de {preferred_name}. Não abuse da intimidade.", app.MAIN_KB)
            await app.send(token, chat, SIGAA_SCHEDULE_GUIDE, app.MAIN_KB)
            return True
        return await original_handle_state(db, token, chat, uid, owner, state, payload, message)

    async def handle_message_with_import_guide(db, token, message):
        text = (message.get("text") or "").strip()
        if text == "📥 Importar grade por PDF/texto":
            chat = message.get("chat") or {}
            user = message.get("from") or {}
            chat_id = chat.get("id")
            if chat_id is None:
                return await original_handle_message(db, token, message)
            uid, _, _ = await app.ensure_user(db, int(chat_id), user)
            await app.set_state(db, uid, "import_schedule", {})
            await app.send(token, int(chat_id), IMPORT_SCHEDULE_PROMPT, app.CANCEL_KB)
            return
        return await original_handle_message(db, token, message)

    app.agenda_text = agenda_with_exam_section
    app.handle_state = handle_state_with_first_access_guide
    app.handle_message = handle_message_with_import_guide
