"""Menus enxutos e autoritativos do Butler operacional."""

import app
import course_operational
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


MAIN_KB = [
    ["➕ Adicionar", "🗓️ Hoje"],
    ["🛒 Item faltando", "📚 Matérias"],
    ["🏠 Cotidiano", "🏋️ Musculação"],
    ["📘 Cursos"],
    ["📖 Manual"],
    ["🌙 Day-off"],
]

COTIDIANO_KB = [
    ["✅ Tarefas", "📅 Compromissos"],
    ["🧘 Rotinas", "🎯 Metas"],
    ["🛒 O que está faltando?", "➕ Item faltando"],
    ["📌 Ler/ver depois", "🍽️ RU"],
    ["👤 Como me chamar", "🏠 Menu principal"],
]

ADD_KB = [
    ["✅ Tarefa", "📅 Compromisso"],
    ["🧘 Rotinas", "🎯 Metas"],
    ["➕ Item faltando", "🏠 Menu principal"],
]

RU_PUBLIC_KB = [
    ["🍽️ Cardápio de hoje", "📅 Cardápio da semana"],
    ["🗃️ Cardápios anteriores"],
    ["⬅️ Voltar ao cotidiano"],
]
RU_OWNER_KB = [
    ["🍽️ Cardápio de hoje", "📅 Cardápio da semana"],
    ["📤 Atualizar cardápio RU", "🗃️ Cardápios anteriores"],
    ["⬅️ Voltar ao cotidiano"],
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
    app.MAIN_KB = [list(row) for row in MAIN_KB]
    app.COTIDIANO_KB = [list(row) for row in COTIDIANO_KB]
    # Respostas internas do domínio nunca exibem a ação administrativa para usuários comuns.
    # O proprietário recebe o botão de importação ao abrir explicitamente o menu RU.
    ru_menu.RU_KB = [list(row) for row in RU_PUBLIC_KB]
    goal_operational.install()
    goal_polish.install()
    goal_deadline_patch.install()
    goal_routine_bridge.install()

    try:
        runtime_guard.MAIN_KB = [list(row) for row in MAIN_KB]
    except Exception:
        pass
    try:
        runtime_guard.COTIDIANO_KB = [list(row) for row in COTIDIANO_KB]
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

    if text == "🏠 Cotidiano":
        await send_message(
            token,
            chat_id,
            "🏠 Cotidiano. Tarefas, compromissos, rotinas, metas, cardápio do RU, lista para depois e o que está faltando em casa.",
            reply_markup=_kb(COTIDIANO_KB),
        )
        return True

    if text == "➕ Adicionar":
        await send_message(token, chat_id, "O que vamos adicionar?", reply_markup=_kb(ADD_KB))
        return True

    if not uid:
        return False

    if text == "✅ Tarefas":
        await send_message(token, chat_id, await _task_list(db, uid), reply_markup=_kb(runtime_guard.TASK_KB))
        return True

    if text == "📅 Compromissos":
        await send_message(token, chat_id, await _appointment_list(db, uid), reply_markup=_kb(COTIDIANO_KB))
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
        await send_message(token, chat_id, await app.grocery_text(db, uid), reply_markup=_kb(app.GROCERY_KB))
        return True

    if text in ROUTINE_DIRECT_BUTTONS:
        return await runtime_guard.handle_pre_dispatch(db, token, message)

    return False
