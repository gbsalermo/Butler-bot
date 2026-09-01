"""Extensão operacional da Etapa 4 de Cursos.

A autoridade de persistência continua sendo :mod:`course_domain`. Este módulo só
expõe a UX incremental das subetapas 4.3+ e reaproveita o wizard CRUD da 4.2.

Invariantes centrais:
- navegar/abrir conteúdo nunca altera progresso;
- ``Continuar curso`` é consulta pura ao próximo pendente;
- conteúdo e curso só mudam de estado por ação explícita;
- conclusão do último conteúdo não conclui o curso automaticamente.
"""
from __future__ import annotations

import app
import course_domain
import course_operational


_INSTALLED = False
_BASE_SHOW_COURSE = course_operational._show_course
_BASE_SHOW_CONTENT = course_operational._show_content


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


def _course_detail_kb(structure):
    status = structure.get("status")
    if status == "archived":
        return [
            ["🧩 Módulos", "📊 Progresso"],
            ["♻️ Reativar curso"],
            ["⬅️ Voltar aos cursos"],
        ]
    if status == "completed":
        return [
            ["🧩 Módulos", "📊 Progresso"],
            ["↩️ Reabrir curso", "🗄️ Arquivar curso"],
            ["⬅️ Voltar aos cursos"],
        ]
    return [
        ["▶️ Continuar curso", "📊 Progresso"],
        ["🧩 Módulos", "➕ Novo módulo"],
        ["✏️ Editar curso", "🗄️ Arquivar curso"],
        ["🏁 Concluir curso"],
        ["⬅️ Voltar aos cursos"],
    ]


def _content_detail_kb(detail, *, archived=False):
    if archived:
        return [["⬅️ Voltar ao módulo"]]

    rows = []
    if detail.get("status") == "pending":
        rows.append(["✅ Concluir conteúdo", "⏭️ Pular conteúdo"])
    else:
        rows.append(["↩️ Voltar para pendente"])
    rows.extend(
        [
            ["✏️ Editar conteúdo"],
            ["⬅️ Voltar ao módulo"],
        ]
    )
    return rows


async def _show_course(db, token, chat_id, uid, course_id):
    try:
        structure = await course_domain.course_structure(db, uid, course_id)
        progress = await course_domain.progress_summary(db, uid, course_id)
    except LookupError:
        await course_operational._send(
            token,
            chat_id,
            "Não encontrei esse curso na sua conta.",
            course_operational.COURSES_KB,
        )
        return False

    description = structure.get("description") or "sem descrição"
    lines = [
        f"📘 {structure['title']}",
        f"Tipo: {course_operational.MODE_LABELS.get(structure['mode'], structure['mode'])}",
        f"Status: {course_operational.STATUS_LABELS.get(structure['status'], structure['status'])}",
        f"Descrição: {description}",
        "",
        f"Módulos: {len(structure['modules'])}",
        f"Conteúdos: {progress['total']}",
        f"Concluídos: {progress['completed']} ({progress['percent_completed']}%)",
        f"Pulados: {progress['skipped']}",
        f"Pendentes: {progress['pending']}",
    ]
    if progress["skipped"]:
        lines.append(f"Resolvidos incluindo pulos: {progress['percent_resolved']}%")
    lines.append("\nProgresso só muda quando você conclui, pula ou reabre algo explicitamente.")

    await app.set_state(db, uid, "course_view", {"course_id": int(course_id)})
    await course_operational._send(
        token,
        chat_id,
        "\n".join(lines),
        _course_detail_kb(structure),
    )
    return True


async def _show_content(db, token, chat_id, uid, course_id, module_id, content_id):
    try:
        detail = await course_domain.content_details(db, uid, course_id, content_id)
        structure = await course_domain.course_structure(db, uid, course_id)
    except LookupError:
        await course_operational._send(
            token,
            chat_id,
            "Não encontrei esse conteúdo nesse curso.",
            course_operational.COURSES_KB,
        )
        return False

    if int(detail["module_id"]) != int(module_id):
        await course_operational._send(
            token,
            chat_id,
            "Esse conteúdo não pertence ao módulo aberto.",
            course_operational.COURSES_KB,
        )
        return False

    lines = [
        f"📄 {detail['title']}",
        f"Módulo: {detail['module_title']}",
        f"Tipo: {course_operational.KIND_LABELS.get(detail['kind'], detail['kind'])}",
        f"Status: {course_operational.CONTENT_STATUS_LABELS.get(detail['status'], detail['status'])}",
    ]
    if detail.get("scheduled_at"):
        lines.append(f"Data/horário: {detail['scheduled_at'].replace('T', ' ')}")
    if detail.get("notes"):
        lines.append(f"Notas: {detail['notes']}")

    if detail["materials"]:
        lines.append("\n📎 Materiais")
        for item in detail["materials"]:
            lines.append(f"• {item['title']} ({item['kind']})")
    if detail["activities"]:
        lines.append("\n📝 Atividades")
        for item in detail["activities"]:
            label = course_operational.CONTENT_STATUS_LABELS.get(item["status"], item["status"])
            lines.append(f"• {item['title']} — {label}")

    lines.append("\nAbrir esta tela não altera o progresso.")
    await app.set_state(
        db,
        uid,
        "course_content_view",
        {
            "course_id": int(course_id),
            "module_id": int(module_id),
            "content_id": int(content_id),
        },
    )
    await course_operational._send(
        token,
        chat_id,
        "\n".join(lines),
        _content_detail_kb(detail, archived=structure.get("status") == "archived"),
    )
    return True


async def _show_progress(db, token, chat_id, uid, course_id):
    try:
        course = await course_domain.get_course(db, uid, course_id)
        progress = await course_domain.progress_summary(db, uid, course_id)
        next_item = await course_domain.next_content(db, uid, course_id)
    except LookupError:
        return await _show_course(db, token, chat_id, uid, course_id)

    lines = [
        f"📊 Progresso — {_row(course, 'title')}",
        f"• Conteúdos: {progress['total']}",
        f"• Concluídos: {progress['completed']} ({progress['percent_completed']}%)",
        f"• Pulados: {progress['skipped']}",
        f"• Pendentes: {progress['pending']}",
        f"• Resolvidos: {progress['percent_resolved']}%",
    ]
    if next_item:
        schedule = _row(next_item, "scheduled_at")
        suffix = f" — {str(schedule).replace('T', ' ')}" if schedule else ""
        lines.append(
            f"\n▶️ Próximo: {_row(next_item, 'module_title')} → {_row(next_item, 'title')}{suffix}"
        )
    else:
        lines.append("\n✅ Não há conteúdo pendente. O curso só termina quando você o conclui explicitamente.")

    await app.set_state(db, uid, "course_view", {"course_id": int(course_id)})
    structure = await course_domain.course_structure(db, uid, course_id)
    await course_operational._send(token, chat_id, "\n".join(lines), _course_detail_kb(structure))
    return True


async def _continue_course(db, token, chat_id, uid, course_id):
    try:
        course = await course_domain.get_course(db, uid, course_id)
        next_item = await course_domain.next_content(db, uid, course_id)
    except LookupError:
        return await _show_course(db, token, chat_id, uid, course_id)

    if not course:
        return await _show_course(db, token, chat_id, uid, course_id)
    if _row(course, "status") in {"archived", "completed"}:
        await course_operational._send(
            token,
            chat_id,
            "Esse curso não está ativo. Reative/reabra antes de continuar.",
            None,
        )
        return await _show_course(db, token, chat_id, uid, course_id)
    if not next_item:
        await course_operational._send(
            token,
            chat_id,
            "✅ Não há conteúdo pendente. Se terminou de verdade, use Concluir curso; nada será concluído automaticamente.",
            None,
        )
        return await _show_course(db, token, chat_id, uid, course_id)

    return await _show_content(
        db,
        token,
        chat_id,
        uid,
        course_id,
        int(_row(next_item, "module_id")),
        int(_row(next_item, "id")),
    )


async def handle_message(db, token, message, *, uid=None, state=None, payload=None):
    """Consome apenas ações novas da Etapa 4.3; o CRUD antigo segue no handler 4.2."""
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None or not uid:
        return False
    chat_id = int(chat_id)
    payload = payload or {}

    if state == "course_view":
        course_id = int(payload["course_id"])
        if text == "▶️ Continuar curso":
            return await _continue_course(db, token, chat_id, uid, course_id)
        if text == "📊 Progresso":
            return await _show_progress(db, token, chat_id, uid, course_id)
        if text == "🏁 Concluir curso":
            course = await course_domain.get_course(db, uid, course_id)
            if not course:
                return await _show_course(db, token, chat_id, uid, course_id)
            await app.set_state(db, uid, "course_complete_confirm", {"course_id": course_id})
            await course_operational._send(
                token,
                chat_id,
                f"🏁 Concluir {_row(course, 'title')}? Essa ação é explícita e independente do status dos conteúdos.",
                [["🏁 Confirmar conclusão"], ["❌ Cancelar ação"]],
            )
            return True
        if text == "↩️ Reabrir curso":
            await course_domain.set_course_status(db, uid, course_id, "active")
            await course_operational._send(token, chat_id, "↩️ Curso reaberto.", None)
            return await _show_course(db, token, chat_id, uid, course_id)

    if state == "course_complete_confirm":
        course_id = int(payload["course_id"])
        if text != "🏁 Confirmar conclusão":
            return False
        await course_domain.set_course_status(db, uid, course_id, "completed")
        await course_operational._send(
            token,
            chat_id,
            "🏁 Curso concluído explicitamente. O histórico e a estrutura foram preservados.",
            None,
        )
        return await _show_course(db, token, chat_id, uid, course_id)

    if state == "course_content_view":
        course_id = int(payload["course_id"])
        module_id = int(payload["module_id"])
        content_id = int(payload["content_id"])
        action = {
            "✅ Concluir conteúdo": "completed",
            "⏭️ Pular conteúdo": "skipped",
            "↩️ Voltar para pendente": "pending",
        }.get(text)
        if action:
            await course_domain.set_content_status(db, uid, course_id, content_id, action)
            messages = {
                "completed": "✅ Conteúdo marcado como concluído.",
                "skipped": "⏭️ Conteúdo pulado. Ele conta como resolvido, não como aprendido/concluído.",
                "pending": "↩️ Conteúdo voltou para pendente.",
            }
            await course_operational._send(token, chat_id, messages[action], None)
            return await _show_content(db, token, chat_id, uid, course_id, module_id, content_id)

    return False


def install():
    """Faz os fluxos CRUD existentes renderizarem as telas enriquecidas da 4.3."""
    global _INSTALLED
    if _INSTALLED:
        return
    course_operational._show_course = _show_course
    course_operational._show_content = _show_content
    _INSTALLED = True
