"""Interface operacional de Cursos no Telegram — Etapa 4.2.

A camada conversa com o usuário e mantém apenas estado de wizard. Toda escrita do
domínio de cursos passa por ``course_domain``. A Etapa 4.2 não conclui conteúdos,
não inicia Modo Estudo e não importa cursos automaticamente.
"""
from __future__ import annotations

from datetime import datetime
import re

import app
import course_domain
from telegram_api import send_message

COURSES_KB = [
    ["📚 Meus cursos", "➕ Novo curso"],
    ["🗄️ Cursos arquivados"],
    ["🏠 Menu principal"],
]
MODE_KB = [
    ["🧭 Autogerido", "📡 Ao vivo"],
    ["❌ Cancelar ação"],
]
DESCRIPTION_KB = [
    ["⏭️ Sem descrição"],
    ["❌ Cancelar ação"],
]
COURSE_EDIT_KB = [
    ["✏️ Nome", "📝 Descrição"],
    ["🔀 Tipo do curso"],
    ["⬅️ Voltar ao curso", "❌ Cancelar ação"],
]
ARCHIVE_CONFIRM_KB = [
    ["✅ Arquivar curso", "❌ Cancelar ação"],
]
CONTENT_KIND_KB = [
    ["🎥 Aula", "📖 Leitura"],
    ["🧪 Exercício", "🛠️ Projeto"],
    ["🔁 Revisão", "📎 Outro"],
    ["❌ Cancelar ação"],
]
SCHEDULE_KB = [
    ["⏭️ Sem data fixa"],
    ["❌ Cancelar ação"],
]

MODE_VALUES = {
    "🧭 Autogerido": "self_paced",
    "📡 Ao vivo": "live",
}
KIND_VALUES = {
    "🎥 Aula": "lesson",
    "📖 Leitura": "reading",
    "🧪 Exercício": "exercise",
    "🛠️ Projeto": "project",
    "🔁 Revisão": "review",
    "📎 Outro": "other",
}
MODE_LABELS = {"self_paced": "🧭 Autogerido", "live": "📡 Ao vivo"}
STATUS_LABELS = {
    "active": "▶️ Ativo",
    "paused": "⏸️ Pausado",
    "completed": "✅ Concluído",
    "archived": "🗄️ Arquivado",
}
KIND_LABELS = {
    "lesson": "🎥 Aula",
    "reading": "📖 Leitura",
    "exercise": "🧪 Exercício",
    "project": "🛠️ Projeto",
    "review": "🔁 Revisão",
    "other": "📎 Outro",
}
CONTENT_STATUS_LABELS = {
    "pending": "⏳ Pendente",
    "completed": "✅ Concluído",
    "skipped": "⏭️ Pulado",
}

COURSE_BUTTON_RE = re.compile(r"^[📘🗄️]\s+#(\d+)\b")
MODULE_BUTTON_RE = re.compile(r"^🧩\s+#(\d+)\b")
CONTENT_BUTTON_RE = re.compile(r"^📄\s+#(\d+)\b")
COURSE_DIRECT_TEXTS = {
    "📘 Cursos",
    "📚 Meus cursos",
    "➕ Novo curso",
    "🗄️ Cursos arquivados",
    "⬅️ Voltar aos cursos",
    "⬅️ Voltar ao curso",
    "⬅️ Voltar ao módulo",
    "🧩 Módulos",
    "➕ Novo módulo",
    "➕ Novo conteúdo",
    "✏️ Editar curso",
    "🗄️ Arquivar curso",
    "♻️ Reativar curso",
    "✏️ Renomear módulo",
    "✏️ Editar conteúdo",
    "✏️ Nome",
    "📝 Descrição",
    "🔀 Tipo do curso",
    "🧹 Limpar descrição",
    "📅 Data/horário",
    "🏷️ Tipo do conteúdo",
}


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


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


async def _send(token, chat_id, text, rows=None):
    await send_message(token, int(chat_id), text, reply_markup=_kb(rows) if rows else None)


def _course_button(course, *, archived=False):
    icon = "🗄️" if archived else "📘"
    title = str(_row(course, "title", "Curso"))
    if len(title) > 36:
        title = title[:33].rstrip() + "..."
    return f"{icon} #{int(_row(course, 'id'))} {title}"


def _module_button(module):
    title = str(module.get("title") or "Módulo")
    if len(title) > 34:
        title = title[:31].rstrip() + "..."
    return f"🧩 #{int(module['id'])} {title}"


def _content_button(content):
    title = str(content.get("title") or "Conteúdo")
    if len(title) > 34:
        title = title[:31].rstrip() + "..."
    return f"📄 #{int(content['id'])} {title}"


def _course_id_from_text(text):
    match = COURSE_BUTTON_RE.match(text or "")
    return int(match.group(1)) if match else None


def _module_id_from_text(text):
    match = MODULE_BUTTON_RE.match(text or "")
    return int(match.group(1)) if match else None


def _content_id_from_text(text):
    match = CONTENT_BUTTON_RE.match(text or "")
    return int(match.group(1)) if match else None


def _parse_schedule(text):
    raw = (text or "").strip()
    if raw in {"⏭️ Sem data fixa", "sem data", "sem data fixa", "nenhuma"}:
        return None, None

    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %Hh%M", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%Y-%m-%dT%H:%M"), None
        except ValueError:
            pass
    return None, "Use `DD/MM/AAAA HH:MM`, por exemplo `15/09/2026 19:30`, ou escolha Sem data fixa."


def _course_detail_kb(structure):
    if structure.get("status") == "archived":
        return [
            ["🧩 Módulos"],
            ["♻️ Reativar curso"],
            ["⬅️ Voltar aos cursos"],
        ]
    return [
        ["🧩 Módulos", "➕ Novo módulo"],
        ["✏️ Editar curso", "🗄️ Arquivar curso"],
        ["⬅️ Voltar aos cursos"],
    ]


def _module_detail_kb(module):
    return [
        ["➕ Novo conteúdo", "✏️ Renomear módulo"],
        ["⬅️ Voltar ao curso"],
    ]


def _content_detail_kb():
    return [
        ["✏️ Editar conteúdo"],
        ["⬅️ Voltar ao módulo"],
    ]


async def _show_course_menu(token, chat_id):
    await _send(
        token,
        chat_id,
        "📘 Cursos e trilhas\n\nAqui ficam cursos estruturados de verdade: módulos, conteúdos, materiais e atividades. A categoria 🎓 Cursos de Ler/Ver Depois continua sendo só uma lista para lembrar depois.",
        COURSES_KB,
    )


async def _show_course_list(db, token, chat_id, uid, *, archived=False):
    statuses = ("archived",) if archived else ("active", "paused", "completed")
    courses = await course_domain.list_courses(db, uid, statuses=statuses)
    if not courses:
        label = "arquivados" if archived else "cadastrados"
        await _send(token, chat_id, f"📘 Você ainda não tem cursos {label}.", COURSES_KB)
        return

    lines = ["🗄️ Cursos arquivados" if archived else "📚 Meus cursos"]
    buttons = []
    for course in courses[:30]:
        status = STATUS_LABELS.get(_row(course, "status"), _row(course, "status"))
        mode = MODE_LABELS.get(_row(course, "mode"), _row(course, "mode"))
        lines.append(f"#{_row(course, 'id')} • {_row(course, 'title')} — {mode} — {status}")
        buttons.append([_course_button(course, archived=archived)])
    buttons.append(["⬅️ Voltar aos cursos"])
    await _send(token, chat_id, "\n".join(lines), buttons)


async def _show_course(db, token, chat_id, uid, course_id):
    try:
        structure = await course_domain.course_structure(db, uid, course_id)
        progress = await course_domain.progress_summary(db, uid, course_id)
    except LookupError:
        await _send(token, chat_id, "Não encontrei esse curso na sua conta.", COURSES_KB)
        return False

    description = structure.get("description") or "sem descrição"
    lines = [
        f"📘 {structure['title']}",
        f"Tipo: {MODE_LABELS.get(structure['mode'], structure['mode'])}",
        f"Status: {STATUS_LABELS.get(structure['status'], structure['status'])}",
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
    lines.append("\nO progresso aqui é somente leitura nesta subetapa; nada é concluído por tempo ou navegação.")
    await app.set_state(db, uid, "course_view", {"course_id": int(course_id)})
    await _send(token, chat_id, "\n".join(lines), _course_detail_kb(structure))
    return True


async def _show_modules(db, token, chat_id, uid, course_id):
    try:
        structure = await course_domain.course_structure(db, uid, course_id)
    except LookupError:
        await _send(token, chat_id, "Não encontrei esse curso.", COURSES_KB)
        return False

    modules = structure["modules"]
    if not modules:
        await app.set_state(db, uid, "course_view", {"course_id": int(course_id)})
        await _send(
            token,
            chat_id,
            f"🧩 {structure['title']} ainda não tem módulos.",
            _course_detail_kb(structure),
        )
        return True

    lines = [f"🧩 Módulos — {structure['title']}"]
    buttons = []
    for module in modules:
        lines.append(f"{module['position']}. {module['title']} — {len(module['contents'])} conteúdo(s)")
        buttons.append([_module_button(module)])
    if structure.get("status") != "archived":
        buttons.append(["➕ Novo módulo"])
    buttons.append(["⬅️ Voltar ao curso"])
    await app.set_state(db, uid, "course_modules", {"course_id": int(course_id)})
    await _send(token, chat_id, "\n".join(lines), buttons)
    return True


async def _find_module(db, uid, course_id, module_id):
    structure = await course_domain.course_structure(db, uid, course_id)
    for module in structure["modules"]:
        if int(module["id"]) == int(module_id):
            return structure, module
    return structure, None


async def _show_module(db, token, chat_id, uid, course_id, module_id):
    try:
        structure, module = await _find_module(db, uid, course_id, module_id)
    except LookupError:
        module = None
        structure = None
    if not module:
        await _send(token, chat_id, "Não encontrei esse módulo nesse curso.", COURSES_KB)
        return False

    lines = [
        f"🧩 {module['title']}",
        f"Curso: {structure['title']}",
        f"Posição: {module['position']}",
    ]
    if module.get("description"):
        lines.append(f"Descrição: {module['description']}")
    if not module["contents"]:
        lines.append("\nNenhum conteúdo cadastrado.")
    else:
        lines.append("\nConteúdos:")
        for content in module["contents"]:
            lines.append(
                f"{content['position']}. {content['title']} — "
                f"{KIND_LABELS.get(content['kind'], content['kind'])} — "
                f"{CONTENT_STATUS_LABELS.get(content['status'], content['status'])}"
            )

    buttons = [[_content_button(item)] for item in module["contents"][:30]]
    if structure.get("status") != "archived":
        buttons.extend(_module_detail_kb(module)[:-1])
    buttons.append(["⬅️ Voltar ao curso"])
    await app.set_state(
        db,
        uid,
        "course_module_view",
        {"course_id": int(course_id), "module_id": int(module_id)},
    )
    await _send(token, chat_id, "\n".join(lines), buttons)
    return True


async def _show_content(db, token, chat_id, uid, course_id, module_id, content_id):
    try:
        detail = await course_domain.content_details(db, uid, course_id, content_id)
        structure = await course_domain.course_structure(db, uid, course_id)
    except LookupError:
        await _send(token, chat_id, "Não encontrei esse conteúdo nesse curso.", COURSES_KB)
        return False
    if int(detail["module_id"]) != int(module_id):
        await _send(token, chat_id, "Esse conteúdo não pertence ao módulo aberto.", COURSES_KB)
        return False

    lines = [
        f"📄 {detail['title']}",
        f"Módulo: {detail['module_title']}",
        f"Tipo: {KIND_LABELS.get(detail['kind'], detail['kind'])}",
        f"Status: {CONTENT_STATUS_LABELS.get(detail['status'], detail['status'])}",
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
            lines.append(f"• {item['title']} — {CONTENT_STATUS_LABELS.get(item['status'], item['status'])}")

    rows = _content_detail_kb() if structure.get("status") != "archived" else [["⬅️ Voltar ao módulo"]]
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
    await _send(token, chat_id, "\n".join(lines), rows)
    return True


async def _finish_create_course(db, token, chat_id, uid, payload, description):
    course_id = await course_domain.create_course(
        db,
        uid,
        payload["title"],
        mode=payload["mode"],
        description=description,
    )
    await app.clear_state(db, uid)
    await _send(token, chat_id, f"✅ Curso criado: {payload['title']}.", COURSES_KB)
    await _show_course(db, token, chat_id, uid, course_id)


async def _finish_add_content(db, token, chat_id, uid, payload, *, scheduled_at=None):
    content_id = await course_domain.add_content(
        db,
        uid,
        payload["course_id"],
        payload["module_id"],
        payload["title"],
        kind=payload["kind"],
        scheduled_at=scheduled_at,
    )
    await app.clear_state(db, uid)
    await _send(token, chat_id, f"✅ Conteúdo adicionado: {payload['title']}.", None)
    await _show_content(
        db,
        token,
        chat_id,
        uid,
        payload["course_id"],
        payload["module_id"],
        content_id,
    )


async def _handle_state(db, token, chat_id, uid, text, state, payload):
    if not state or not state.startswith("course_"):
        return False

    if text in {"❌ Cancelar ação", "/cancelar"}:
        course_id = payload.get("course_id")
        await app.clear_state(db, uid)
        if course_id:
            await _send(token, chat_id, "Operação cancelada. Nada foi alterado.", None)
            return await _show_course(db, token, chat_id, uid, int(course_id))
        await _send(token, chat_id, "Operação cancelada. Nada foi alterado.", COURSES_KB)
        return True

    if state == "course_create_title":
        title = " ".join(text.split()).strip()
        if not title or len(title) > 180:
            await _send(token, chat_id, "Informe um nome entre 1 e 180 caracteres.", [["❌ Cancelar ação"]])
            return True
        await app.set_state(db, uid, "course_create_mode", {"title": title})
        await _send(token, chat_id, "Que tipo de curso é?", MODE_KB)
        return True

    if state == "course_create_mode":
        mode = MODE_VALUES.get(text)
        if not mode:
            await _send(token, chat_id, "Escolha Autogerido ou Ao vivo.", MODE_KB)
            return True
        payload["mode"] = mode
        await app.set_state(db, uid, "course_create_description", payload)
        await _send(token, chat_id, "Quer adicionar uma descrição? Pode escrever ou escolher Sem descrição.", DESCRIPTION_KB)
        return True

    if state == "course_create_description":
        description = None if text == "⏭️ Sem descrição" else text.strip()
        await _finish_create_course(db, token, chat_id, uid, payload, description)
        return True

    if state == "course_view":
        course_id = int(payload["course_id"])
        if text == "🧩 Módulos":
            return await _show_modules(db, token, chat_id, uid, course_id)
        if text == "➕ Novo módulo":
            await app.set_state(db, uid, "course_add_module_title", {"course_id": course_id})
            await _send(token, chat_id, "Nome do novo módulo?", [["❌ Cancelar ação"]])
            return True
        if text == "✏️ Editar curso":
            await app.set_state(db, uid, "course_edit_menu", {"course_id": course_id})
            await _send(token, chat_id, "O que quer editar?", COURSE_EDIT_KB)
            return True
        if text == "🗄️ Arquivar curso":
            course = await course_domain.get_course(db, uid, course_id)
            if not course:
                await app.clear_state(db, uid)
                return await _show_course_menu(token, chat_id)
            await app.set_state(db, uid, "course_archive_confirm", {"course_id": course_id})
            await _send(
                token,
                chat_id,
                f"Arquivar {_row(course, 'title')}? Isso tira o curso da lista principal, mas preserva estrutura e histórico.",
                ARCHIVE_CONFIRM_KB,
            )
            return True
        if text == "♻️ Reativar curso":
            await course_domain.set_course_status(db, uid, course_id, "active")
            await app.clear_state(db, uid)
            await _send(token, chat_id, "♻️ Curso reativado.", None)
            return await _show_course(db, token, chat_id, uid, course_id)
        if text == "⬅️ Voltar aos cursos":
            await app.clear_state(db, uid)
            await _show_course_menu(token, chat_id)
            return True

    if state == "course_archive_confirm":
        course_id = int(payload["course_id"])
        if text != "✅ Arquivar curso":
            await _send(token, chat_id, "Confirme em Arquivar curso ou cancele.", ARCHIVE_CONFIRM_KB)
            return True
        await course_domain.set_course_status(db, uid, course_id, "archived")
        await app.clear_state(db, uid)
        await _send(token, chat_id, "🗄️ Curso arquivado. Nada do histórico foi apagado.", COURSES_KB)
        return True

    if state == "course_edit_menu":
        course_id = int(payload["course_id"])
        if text == "✏️ Nome":
            await app.set_state(db, uid, "course_edit_name", payload)
            await _send(token, chat_id, "Qual será o novo nome?", [["❌ Cancelar ação"]])
            return True
        if text == "📝 Descrição":
            await app.set_state(db, uid, "course_edit_description", payload)
            await _send(
                token,
                chat_id,
                "Escreva a nova descrição ou escolha Limpar descrição.",
                [["🧹 Limpar descrição"], ["❌ Cancelar ação"]],
            )
            return True
        if text == "🔀 Tipo do curso":
            await app.set_state(db, uid, "course_edit_mode", payload)
            await _send(token, chat_id, "Novo tipo do curso?", MODE_KB)
            return True
        if text == "⬅️ Voltar ao curso":
            return await _show_course(db, token, chat_id, uid, course_id)
        await _send(token, chat_id, "Escolha Nome, Descrição ou Tipo do curso.", COURSE_EDIT_KB)
        return True

    if state == "course_edit_name":
        course_id = int(payload["course_id"])
        try:
            await course_domain.update_course(db, uid, course_id, title=text)
        except ValueError:
            await _send(token, chat_id, "Informe um nome válido de até 180 caracteres.", [["❌ Cancelar ação"]])
            return True
        await _send(token, chat_id, "✅ Nome atualizado.", None)
        return await _show_course(db, token, chat_id, uid, course_id)

    if state == "course_edit_description":
        course_id = int(payload["course_id"])
        description = None if text == "🧹 Limpar descrição" else text
        await course_domain.update_course(db, uid, course_id, description=description)
        await _send(token, chat_id, "✅ Descrição atualizada.", None)
        return await _show_course(db, token, chat_id, uid, course_id)

    if state == "course_edit_mode":
        course_id = int(payload["course_id"])
        mode = MODE_VALUES.get(text)
        if not mode:
            await _send(token, chat_id, "Escolha Autogerido ou Ao vivo.", MODE_KB)
            return True
        await course_domain.update_course(db, uid, course_id, mode=mode)
        await _send(token, chat_id, "✅ Tipo do curso atualizado. Isso não altera progresso nem desloca conteúdos.", None)
        return await _show_course(db, token, chat_id, uid, course_id)

    if state == "course_add_module_title":
        course_id = int(payload["course_id"])
        try:
            module_id = await course_domain.add_module(db, uid, course_id, text)
        except ValueError:
            await _send(token, chat_id, "Informe um nome válido para o módulo.", [["❌ Cancelar ação"]])
            return True
        await _send(token, chat_id, "✅ Módulo adicionado.", None)
        return await _show_module(db, token, chat_id, uid, course_id, module_id)

    if state == "course_modules":
        course_id = int(payload["course_id"])
        module_id = _module_id_from_text(text)
        if module_id is not None:
            return await _show_module(db, token, chat_id, uid, course_id, module_id)
        if text == "➕ Novo módulo":
            await app.set_state(db, uid, "course_add_module_title", {"course_id": course_id})
            await _send(token, chat_id, "Nome do novo módulo?", [["❌ Cancelar ação"]])
            return True
        if text == "⬅️ Voltar ao curso":
            return await _show_course(db, token, chat_id, uid, course_id)

    if state == "course_module_view":
        course_id = int(payload["course_id"])
        module_id = int(payload["module_id"])
        content_id = _content_id_from_text(text)
        if content_id is not None:
            return await _show_content(db, token, chat_id, uid, course_id, module_id, content_id)
        if text == "➕ Novo conteúdo":
            await app.set_state(
                db,
                uid,
                "course_add_content_title",
                {"course_id": course_id, "module_id": module_id},
            )
            await _send(token, chat_id, "Nome do novo conteúdo/aula?", [["❌ Cancelar ação"]])
            return True
        if text == "✏️ Renomear módulo":
            await app.set_state(
                db,
                uid,
                "course_rename_module",
                {"course_id": course_id, "module_id": module_id},
            )
            await _send(token, chat_id, "Novo nome do módulo?", [["❌ Cancelar ação"]])
            return True
        if text == "⬅️ Voltar ao curso":
            return await _show_course(db, token, chat_id, uid, course_id)

    if state == "course_rename_module":
        course_id = int(payload["course_id"])
        module_id = int(payload["module_id"])
        try:
            await course_domain.rename_module(db, uid, course_id, module_id, text)
        except ValueError:
            await _send(token, chat_id, "Informe um nome válido para o módulo.", [["❌ Cancelar ação"]])
            return True
        await _send(token, chat_id, "✅ Módulo renomeado.", None)
        return await _show_module(db, token, chat_id, uid, course_id, module_id)

    if state == "course_add_content_title":
        title = " ".join(text.split()).strip()
        if not title or len(title) > 180:
            await _send(token, chat_id, "Informe um nome válido para o conteúdo.", [["❌ Cancelar ação"]])
            return True
        payload["title"] = title
        await app.set_state(db, uid, "course_add_content_kind", payload)
        await _send(token, chat_id, "Que tipo de conteúdo é?", CONTENT_KIND_KB)
        return True

    if state == "course_add_content_kind":
        kind = KIND_VALUES.get(text)
        if not kind:
            await _send(token, chat_id, "Escolha um dos tipos mostrados.", CONTENT_KIND_KB)
            return True
        payload["kind"] = kind
        course = await course_domain.get_course(db, uid, payload["course_id"])
        if course and _row(course, "mode") == "live":
            await app.set_state(db, uid, "course_add_content_schedule", payload)
            await _send(
                token,
                chat_id,
                "Como é ao vivo, informe data e hora (`DD/MM/AAAA HH:MM`) ou deixe Sem data fixa.",
                SCHEDULE_KB,
            )
            return True
        await _finish_add_content(db, token, chat_id, uid, payload)
        return True

    if state == "course_add_content_schedule":
        scheduled_at, error = _parse_schedule(text)
        if error:
            await _send(token, chat_id, error, SCHEDULE_KB)
            return True
        await _finish_add_content(db, token, chat_id, uid, payload, scheduled_at=scheduled_at)
        return True

    if state == "course_content_view":
        course_id = int(payload["course_id"])
        module_id = int(payload["module_id"])
        content_id = int(payload["content_id"])
        if text == "✏️ Editar conteúdo":
            await app.set_state(db, uid, "course_content_edit_menu", payload)
            await _send(
                token,
                chat_id,
                "O que quer editar no conteúdo?",
                [["✏️ Nome", "🏷️ Tipo do conteúdo"], ["📅 Data/horário"], ["⬅️ Voltar ao conteúdo"]],
            )
            return True
        if text == "⬅️ Voltar ao módulo":
            return await _show_module(db, token, chat_id, uid, course_id, module_id)

    if state == "course_content_edit_menu":
        course_id = int(payload["course_id"])
        module_id = int(payload["module_id"])
        content_id = int(payload["content_id"])
        if text == "✏️ Nome":
            await app.set_state(db, uid, "course_content_edit_name", payload)
            await _send(token, chat_id, "Novo nome do conteúdo?", [["❌ Cancelar ação"]])
            return True
        if text == "🏷️ Tipo do conteúdo":
            await app.set_state(db, uid, "course_content_edit_kind", payload)
            await _send(token, chat_id, "Novo tipo?", CONTENT_KIND_KB)
            return True
        if text == "📅 Data/horário":
            await app.set_state(db, uid, "course_content_edit_schedule", payload)
            await _send(token, chat_id, "Informe `DD/MM/AAAA HH:MM` ou Sem data fixa.", SCHEDULE_KB)
            return True
        if text == "⬅️ Voltar ao conteúdo":
            return await _show_content(db, token, chat_id, uid, course_id, module_id, content_id)
        return True

    if state == "course_content_edit_name":
        course_id = int(payload["course_id"])
        module_id = int(payload["module_id"])
        content_id = int(payload["content_id"])
        try:
            await course_domain.update_content(db, uid, course_id, content_id, title=text)
        except ValueError:
            await _send(token, chat_id, "Informe um nome válido para o conteúdo.", [["❌ Cancelar ação"]])
            return True
        await _send(token, chat_id, "✅ Conteúdo atualizado.", None)
        return await _show_content(db, token, chat_id, uid, course_id, module_id, content_id)

    if state == "course_content_edit_kind":
        course_id = int(payload["course_id"])
        module_id = int(payload["module_id"])
        content_id = int(payload["content_id"])
        kind = KIND_VALUES.get(text)
        if not kind:
            await _send(token, chat_id, "Escolha um tipo válido.", CONTENT_KIND_KB)
            return True
        await course_domain.update_content(db, uid, course_id, content_id, kind=kind)
        await _send(token, chat_id, "✅ Tipo do conteúdo atualizado.", None)
        return await _show_content(db, token, chat_id, uid, course_id, module_id, content_id)

    if state == "course_content_edit_schedule":
        course_id = int(payload["course_id"])
        module_id = int(payload["module_id"])
        content_id = int(payload["content_id"])
        scheduled_at, error = _parse_schedule(text)
        if error:
            await _send(token, chat_id, error, SCHEDULE_KB)
            return True
        await course_domain.update_content(
            db,
            uid,
            course_id,
            content_id,
            scheduled_at=scheduled_at,
        )
        await _send(token, chat_id, "✅ Data/horário atualizados.", None)
        return await _show_content(db, token, chat_id, uid, course_id, module_id, content_id)

    # Estado de cursos desconhecido é consumido para não cair em outro domínio.
    await _send(token, chat_id, "Não reconheci essa opção dentro de Cursos. Use os botões da tela.", COURSES_KB)
    return True


async def handle_message(db, token, message, *, uid=None, state=None, payload=None):
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if not text or chat_id is None:
        return False
    chat_id = int(chat_id)

    course_state = bool(state and str(state).startswith("course_"))
    direct = (
        text in COURSE_DIRECT_TEXTS
        or _course_id_from_text(text) is not None
        or _module_id_from_text(text) is not None
        or _content_id_from_text(text) is not None
    )
    if not course_state and not direct:
        return False
    if uid is None:
        row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
        uid = int(_row(row, "id")) if row else None
    if uid is None:
        return False
    if state is None:
        state, payload = await app.get_state(db, uid)
    payload = payload or {}

    if await _handle_state(db, token, chat_id, uid, text, state, payload):
        return True

    if text in {"📘 Cursos", "⬅️ Voltar aos cursos"}:
        await app.clear_state(db, uid)
        await _show_course_menu(token, chat_id)
        return True
    if text == "📚 Meus cursos":
        await app.clear_state(db, uid)
        await _show_course_list(db, token, chat_id, uid, archived=False)
        return True
    if text == "🗄️ Cursos arquivados":
        await app.clear_state(db, uid)
        await _show_course_list(db, token, chat_id, uid, archived=True)
        return True
    if text == "➕ Novo curso":
        await app.set_state(db, uid, "course_create_title", {})
        await _send(token, chat_id, "Qual o nome do curso?", [["❌ Cancelar ação"]])
        return True

    course_id = _course_id_from_text(text)
    if course_id is not None:
        return await _show_course(db, token, chat_id, uid, course_id)

    return False
