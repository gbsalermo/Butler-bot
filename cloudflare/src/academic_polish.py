from datetime import date

import app
import quality_patch
import academic_intelligence


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

    app.agenda_text = agenda_with_exam_section
