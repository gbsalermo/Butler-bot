"""Menus enxutos e autoritativos do Butler operacional.

O fechamento da Etapa 4 usa uma raiz minimalista e organiza descoberta por áreas
humanas. Regras de negócio continuam nos módulos de domínio; este arquivo só
orquestra navegação, atalhos e compatibilidade com rótulos antigos.
"""

import app
import course_operational
import course_stage4
import runtime_guard
import ru_menu
import goal_operational
import goal_polish
import goal_deadline_patch
import goal_routine_bridge
import goal_natural_patch
from owner_profile import is_owner
from task_context_patch import _task_list
from telegram_api import send_message


# Raiz aprovada para o fechamento da Etapa 4.
MAIN_KB = [
    ["➕ Adicionar", "🗓️ Hoje"],
    ["🎓 Faculdade", "📋 Minha vida"],
    ["🏋️ Treino", "⚙️ Mais"],
    ["🌙 Day-off"],
]

FACULTY_KB = [
    ["📚 Matérias", "🍽️ RU"],
    ["🧠 Modo Estudo", "📘 Cursos"],
    ["⬅️ Início"],
]

MY_LIFE_KB = [
    ["✅ Tarefas", "📅 Compromissos"],
    ["🧘 Rotinas", "🎯 Metas"],
    ["🛒 Casa", "📌 Interesses"],
    ["⬅️ Início"],
]

# Alias de compatibilidade: módulos antigos ainda referenciam app.COTIDIANO_KB.
COTIDIANO_KB = MY_LIFE_KB

HOUSE_KB = [
    ["🛒 O que está faltando?", "➕ Item faltando"],
    ["⬅️ Minha vida"],
]

MORE_KB = [
    ["👤 Como me chamar", "📖 Manual"],
    ["⬅️ Início"],
]

STUDY_DISCOVERY_KB = [
    ["📊 Status do estudo", "📚 Histórico de estudo"],
    ["⬅️ Faculdade"],
]

ADD_KB = [
    ["✅ Tarefa", "📅 Compromisso"],
    ["🧘 Rotinas", "🎯 Metas"],
    ["➕ Item faltando"],
    ["⬅️ Início"],
]

# Menus locais sincronizados aqui apenas na dimensão de navegação. As ações
# continuam pertencendo aos respectivos domínios.
ACADEMIC_KB = [
    ["📚 Minhas matérias", "⚙️ Gerenciar matérias"],
    ["📝 Adicionar prova", "📋 Provas"],
    ["✏️ Editar prova", "🚫 Cancelar prova"],
    ["📊 Ver faltas", "⚙️ Limite de faltas"],
    ["✏️ Editar limite", "🗑️ Excluir falta"],
    ["📥 Importar grade por PDF/texto"],
    ["⬅️ Faculdade"],
]

TASK_KB = [
    ["✅ Concluir tarefa", "⏰ Adiar tarefa"],
    ["📌 Manter pendente", "🚫 Cancelar tarefa"],
    ["⬅️ Minha vida"],
]

ROUTINE_KB = [
    ["➕ Adicionar rotina", "✏️ Editar rotina"],
    ["📋 Minhas rotinas", "✅ Marcar rotina feita"],
    ["🏁 Encerrar rotina hoje", "🗑️ Remover rotina"],
    ["⬅️ Minha vida"],
]

GOAL_KB = [
    ["➕ Nova meta", "📋 Minhas metas"],
    ["✅ Registrar progresso", "🔗 Vincular rotina"],
    ["✏️ Editar meta", "🏁 Concluir meta"],
    ["🗑️ Remover meta", "⬅️ Minha vida"],
]

COURSES_KB = [
    ["📚 Meus cursos", "➕ Novo curso"],
    ["📥 Importar curso", "🗄️ Cursos arquivados"],
    ["⬅️ Faculdade"],
]

RU_PUBLIC_KB = [
    ["🍽️ Cardápio de hoje", "📅 Cardápio da semana"],
    ["🗃️ Cardápios anteriores"],
    ["⬅️ Faculdade"],
]
RU_OWNER_KB = [
    ["🍽️ Cardápio de hoje", "📅 Cardápio da semana"],
    ["📤 Atualizar cardápio RU", "🗃️ Cardápios anteriores"],
    ["⬅️ Faculdade"],
]
RU_OPEN_TEXTS = {"🍽️ RU", "🍽️ Restaurante Universitário"}
RU_IMPORT_STATES = {"ru_import_wait", "ru_import_confirm"}

ROUTINE_DIRECT_BUTTONS = {
    "🧘 Rotinas",
    "📋 Minhas rotinas",
    "➕ Adicionar rotina",
    "✅ Marcar rotina feita",
    "🗑️ Remover rotina",
}

GOAL_DIRECT_TEXTS = {
    "🎯 Metas",
    "➕ Nova meta",
    "📋 Minhas metas",
    "✅ Registrar progresso",
    "🔗 Vincular rotina",
    "✏️ Editar meta",
    "🏁 Concluir meta",
    "🗑️ Remover meta",
    "🔥 Hábito",
    "📈 Numérica",
    "🏁 Projeto",
    "⬅️ Voltar às metas",
}


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


def _clone(rows):
    return [list(row) for row in rows]


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


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


async def _clear_navigation_state(db, uid):
    """Área/Voltar é sempre rota de fuga de um wizard antigo."""
    if not uid:
        return
    await app.clear_state(db, uid)
    try:
        await runtime_guard._clear(db, uid)
    except Exception:
        pass


def _replace_button(rows, old, new):
    return [[new if button == old else button for button in row] for row in rows]


def _workout_keyboard(chat_id):
    base = app.WORKOUT_KB if is_owner(chat_id) else runtime_guard.GENERIC_WORKOUT_KB
    return _replace_button(base, "🏠 Menu principal", "⬅️ Início")


async def _ru_source_uid(db, fallback_uid):
    """Cardápio RU é compartilhado: todos leem a importação feita pelo proprietário."""
    row = await db.prepare("SELECT id FROM users WHERE is_owner=1 ORDER BY id LIMIT 1").first()
    return int(_row(row, "id")) if row else fallback_uid


def _ru_keyboard(chat_id):
    return RU_OWNER_KB if is_owner(chat_id) else RU_PUBLIC_KB


def _is_ru_import_request(text):
    n = ru_menu._norm(text)
    return text == "📤 Atualizar cardápio RU" or any(
        marker in n for marker in ("atualizar cardapio ru", "importar cardapio ru", "novo cardapio do ru")
    )


def _looks_goal_related(text, state=None):
    if state and state.startswith("goal_"):
        return True
    if text in GOAL_DIRECT_TEXTS:
        return True

    n = goal_operational._norm(text)
    if "meta" in n or "objetivo" in n:
        return True
    if n.startswith("quero perder ") and "kg" in n:
        return True
    if n.startswith(("quero terminar projeto ", "quero terminar o projeto ", "quero finalizar projeto ", "quero concluir projeto ")):
        return True
    return False


async def _appointment_list(db, uid):
    """Pendentes sempre aparecem; resolvidos/cancelados só por 24h."""
    rs = await _rows(db.prepare("""
        SELECT id,title,due_date,due_time,status,completed_at,cancelled_at
        FROM daily_items
        WHERE user_id=? AND kind='compromisso' AND (
            status='pendente'
            OR (status='concluido' AND completed_at IS NOT NULL
                AND datetime(completed_at) >= datetime('now','-24 hours'))
            OR (status='cancelado' AND cancelled_at IS NOT NULL
                AND datetime(cancelled_at) >= datetime('now','-24 hours'))
        )
        ORDER BY CASE status WHEN 'pendente' THEN 0 WHEN 'concluido' THEN 1 ELSE 2 END,
                 COALESCE(due_date,'9999-12-31'), COALESCE(due_time,'99:99'), id
        LIMIT 40
    """).bind(uid))
    if not rs:
        return "📅 Nenhum compromisso ativo. Os antigos continuam no histórico; não precisam morar nesta tela para sempre."
    out = ["📅 Compromissos"]
    for pos, r in enumerate(rs, 1):
        icon = {"pendente":"⏳", "concluido":"✅", "cancelado":"🚫"}.get(_row(r,"status"), "•")
        when = ""
        if _row(r,"due_date"):
            when = f" — {_row(r,'due_date')[8:10]}/{_row(r,'due_date')[5:7]}"
            if _row(r,"due_time"):
                when += f" {_row(r,'due_time')}"
        out.append(f"{icon} {pos}. {_row(r,'title')}{when}")
    out.append("\nPendentes continuam visíveis até serem resolvidos. Concluídos/cancelados saem desta tela após 24h, sem apagar o histórico.")
    return "\n".join(out)


def install():
    """Sincroniza a navegação sem mover regras de negócio para este módulo."""
    app.MAIN_KB = _clone(MAIN_KB)
    app.COTIDIANO_KB = _clone(MY_LIFE_KB)
    app.GROCERY_KB = _clone(HOUSE_KB)
    app.ACADEMIC_KB = _clone(ACADEMIC_KB)
    app.GOALS_KB = _clone(GOAL_KB)
    app.AGENDA_KB = _replace_button(app.AGENDA_KB, "🏠 Menu principal", "⬅️ Início")
    app.WORKOUT_KB = _replace_button(app.WORKOUT_KB, "🏠 Menu principal", "⬅️ Início")

    # Respostas internas do RU nunca exibem a ação administrativa para usuários comuns.
    ru_menu.RU_KB = _clone(RU_PUBLIC_KB)

    # Cursos 4.3+ instala seu menu; depois alinhamos apenas a rota de retorno.
    course_stage4.install()
    course_operational.COURSES_KB = _clone(COURSES_KB)

    goal_operational.install()
    goal_operational.GOAL_KB = _clone(GOAL_KB)
    goal_polish.install()
    goal_deadline_patch.install()
    goal_routine_bridge.install()

    runtime_guard.MAIN_KB = _clone(MAIN_KB)
    runtime_guard.COTIDIANO_KB = _clone(MY_LIFE_KB)
    runtime_guard.TASK_KB = _clone(TASK_KB)
    runtime_guard.ROUTINE_KB = _clone(ROUTINE_KB)
    runtime_guard.GENERIC_WORKOUT_KB = _replace_button(
        runtime_guard.GENERIC_WORKOUT_KB, "🏠 Menu principal", "⬅️ Início"
    )

    # Menus locais continuam nos módulos de domínio, mas recebem a mesma rota de
    # volta para impedir telas que transportem o usuário à hierarquia antiga.
    try:
        import academic_intelligence
        import attendance_production_fix
        import exam_cancel_patch

        academic_intelligence.ACADEMIC_KB = _clone(ACADEMIC_KB)
        exam_cancel_patch.ACADEMIC_KB = _clone(ACADEMIC_KB)
        attendance_production_fix.ACADEMIC_KB_FULL[:] = _clone(ACADEMIC_KB)
    except Exception:
        pass

    try:
        import task_context_patch

        task_context_patch.TASK_KB = _clone(TASK_KB)
    except Exception:
        pass

    try:
        import routine_integration
        import routine_ui_patch
        import quality_patch

        routine_integration.ROUTINE_KB = _clone(ROUTINE_KB)
        routine_ui_patch.ROUTINE_KB = _clone(ROUTINE_KB)
        quality_patch.ROUTINE_KB = _clone(ROUTINE_KB)
        quality_patch.GROCERY_KB = _clone(HOUSE_KB)
    except Exception:
        pass

    try:
        import grocery_phrase_patch

        grocery_phrase_patch.GROCERY_KB = _clone(HOUSE_KB)
    except Exception:
        pass

    try:
        import user_manual

        user_manual.MANUAL_KB["keyboard"] = _replace_button(
            user_manual.MANUAL_KB.get("keyboard", []), "🏠 Menu principal", "⬅️ Início"
        )
    except Exception:
        pass


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    chat_id = int(chat_id)

    # Usuário + estado já vêm do cache por update quando production_usability
    # passou antes deste handler. Mesmo assim, o helper continua seguro isolado.
    uid = await _uid(db, chat_id)
    state, state_payload = await runtime_guard._state(db, uid) if uid else (None, {})
    owner = is_owner(chat_id)

    # Extensões da Etapa 4 (progresso/estudo/importação) têm precedência sobre o
    # CRUD 4.2, mas continuam usando a mesma autoridade course_domain.
    if await course_stage4.handle_message(
        db,
        token,
        message,
        uid=uid,
        state=state,
        payload=state_payload,
    ):
        return True

    # Cursos estruturados usam o mesmo usuário/estado já resolvidos por este menu,
    # evitando uma segunda consulta de estado no caminho interativo.
    if await course_operational.handle_message(
        db,
        token,
        message,
        uid=uid,
        state=state,
        payload=state_payload,
    ):
        return True

    # Navegação de áreas. Rótulos antigos continuam como aliases temporários.
    if text in {"⬅️ Início", "🏠 Menu principal"}:
        await _clear_navigation_state(db, uid)
        await send_message(token, chat_id, "🏠 Início", reply_markup=_kb(MAIN_KB))
        return True

    if text in {"🎓 Faculdade", "⬅️ Faculdade"}:
        await _clear_navigation_state(db, uid)
        await send_message(
            token,
            chat_id,
            "🎓 Faculdade. Matérias, RU e ferramentas de estudo ficam aqui.",
            reply_markup=_kb(FACULTY_KB),
        )
        return True

    if text in {"📋 Minha vida", "🏠 Cotidiano", "⬅️ Minha vida", "⬅️ Voltar ao cotidiano"}:
        await _clear_navigation_state(db, uid)
        await send_message(
            token,
            chat_id,
            "📋 Minha vida. Organização pessoal, casa e interesses sem transformar a raiz num painel de avião.",
            reply_markup=_kb(MY_LIFE_KB),
        )
        return True

    if text == "🛒 Casa":
        await _clear_navigation_state(db, uid)
        await send_message(
            token,
            chat_id,
            "🛒 Casa. O que acabou e o que precisa entrar na lista fica aqui.",
            reply_markup=_kb(HOUSE_KB),
        )
        return True

    if text in {"🏋️ Treino", "🏋️ Musculação"}:
        await _clear_navigation_state(db, uid)
        await send_message(
            token,
            chat_id,
            "🏋️ Treino. Ficha, registro e progresso sem outra camada no caminho.",
            reply_markup=_kb(_workout_keyboard(chat_id)),
        )
        return True

    if text == "⚙️ Mais":
        await _clear_navigation_state(db, uid)
        await send_message(
            token,
            chat_id,
            "⚙️ Mais. Preferências simples e ajuda do Butler.",
            reply_markup=_kb(MORE_KB),
        )
        return True

    if text == "👤 Como me chamar":
        if not uid:
            return False
        await app.set_state(db, uid, "rename", {})
        await send_message(
            token,
            chat_id,
            "Como quer que eu te chame?",
            reply_markup=_kb([["❌ Cancelar ação"]]),
        )
        return True

    if text == "🧠 Modo Estudo":
        await _clear_navigation_state(db, uid)
        await send_message(
            token,
            chat_id,
            "🧠 Modo Estudo\n\n"
            "Para começar, diga por exemplo:\n"
            "`quero estudar Física agora: ondas, exercícios`\n\n"
            "Você também pode consultar o status ou o histórico pelos botões abaixo. "
            "O fim do timer nunca conclui um tópico sozinho.",
            reply_markup=_kb(STUDY_DISCOVERY_KB),
        )
        return True

    # O cardápio é público para todos os usuários, mas a manutenção do TXT fica
    # restrita ao proprietário. Abrir o menu explicitamente usa teclado dinâmico.
    if text in RU_OPEN_TEXTS:
        await send_message(
            token,
            chat_id,
            "🍽️ Restaurante Universitário. Cardápio semanal sem precisar caçar a foto toda vez.",
            reply_markup=_kb(_ru_keyboard(chat_id)),
        )
        return True

    # Proteção dupla: mesmo que um usuário comum ainda tenha um teclado antigo em
    # cache ou digite a frase manualmente, não consegue iniciar/continuar importação.
    if (_is_ru_import_request(text) or state in RU_IMPORT_STATES) and not owner:
        if state in RU_IMPORT_STATES and uid:
            await app.clear_state(db, uid)
        await send_message(
            token,
            chat_id,
            "🍽️ O cardápio do RU é público, mas a atualização do arquivo está restrita ao administrador por enquanto.",
            reply_markup=_kb(RU_PUBLIC_KB),
        )
        return True

    # Todos consultam a mesma fonte: o cardápio importado pelo proprietário.
    # Estado/payload de importação só são encaminhados quando o próprio owner fala.
    ru_uid = await _ru_source_uid(db, uid) if uid else None
    ru_state = state if owner else None
    ru_payload = state_payload if owner else {}
    if await ru_menu.handle_message(db, token, message, uid=ru_uid, state=ru_state, payload=ru_payload):
        return True

    # Metas tinham quatro handlers executados para qualquer texto. Agora só entram
    # quando a conversa realmente está no domínio de metas.
    if _looks_goal_related(text, state):
        if await goal_natural_patch.handle_message(db, token, message):
            return True
        if await goal_deadline_patch.handle_message(db, token, message):
            return True
        if await goal_polish.handle_message(db, token, message):
            return True
        if await goal_operational.handle_message(db, token, message):
            return True

    if text == "➕ Adicionar":
        await _clear_navigation_state(db, uid)
        await send_message(token, chat_id, "O que vamos adicionar?", reply_markup=_kb(ADD_KB))
        return True

    if not uid:
        return False

    if text == "✅ Tarefas":
        await send_message(token, chat_id, await _task_list(db, uid), reply_markup=_kb(runtime_guard.TASK_KB))
        return True

    if text == "📅 Compromissos":
        await send_message(token, chat_id, await _appointment_list(db, uid), reply_markup=_kb(MY_LIFE_KB))
        return True

    if text == "📅 Compromisso":
        await app.set_state(db, uid, "appointment_title", {})
        await send_message(token, chat_id, "Qual compromisso? Ex.: `Dentista`, `Reunião com João`.", reply_markup=_kb(app.CANCEL_KB))
        return True

    if text in ("➕ Item faltando", "➕ Adicionar item"):
        await app.set_state(db, uid, "grocery_add", {})
        await send_message(token, chat_id, "O que está faltando? Pode mandar `sal, açúcar, café`.", reply_markup=_kb(app.CANCEL_KB))
        return True

    if text in ("🛒 O que está faltando?", "🛒 Item faltando", "📋 Ver itens faltando"):
        await send_message(token, chat_id, await app.grocery_text(db, uid), reply_markup=_kb(HOUSE_KB))
        return True

    if text in ROUTINE_DIRECT_BUTTONS:
        return await runtime_guard.handle_pre_dispatch(db, token, message)

    return False
