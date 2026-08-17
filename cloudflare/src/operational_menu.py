"""Menus enxutos e autoritativos do Butler operacional."""

import app
import runtime_guard
import goal_operational
import goal_polish
import goal_deadline_patch
import goal_routine_bridge
import goal_natural_patch
from task_context_patch import _task_list
from telegram_api import send_message


MAIN_KB = [
    ["➕ Adicionar", "🗓️ Hoje"],
    ["🛒 Item faltando", "📚 Matérias"],
    ["🏠 Cotidiano", "🏋️ Musculação"],
    ["🌙 Day-off"],
]

COTIDIANO_KB = [
    ["✅ Tarefas", "📅 Compromissos"],
    ["🧘 Rotinas", "🎯 Metas"],
    ["🛒 O que está faltando?", "➕ Item faltando"],
    ["📌 Ler/ver depois"],
    ["👤 Como me chamar", "🏠 Menu principal"],
]

ADD_KB = [
    ["✅ Tarefa", "📅 Compromisso"],
    ["🧘 Rotinas", "🎯 Metas"],
    ["➕ Item faltando", "🏠 Menu principal"],
]

ROUTINE_DIRECT_BUTTONS = {
    "🧘 Rotinas",
    "📋 Minhas rotinas",
    "➕ Adicionar rotina",
    "✅ Marcar rotina feita",
    "🗑️ Remover rotina",
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


async def _appointment_list(db, uid):
    """Pendentes sempre aparecem; resolvidos/cancelados só por 24h.

    O histórico completo continua preservado em daily_items.
    """
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
    # Metas ficam na frente porque possuem estados/guias próprios.
    if await goal_natural_patch.handle_message(db, token, message):
        return True
    if await goal_deadline_patch.handle_message(db, token, message):
        return True
    if await goal_polish.handle_message(db, token, message):
        return True
    if await goal_operational.handle_message(db, token, message):
        return True

    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    chat_id = int(chat_id)

    if text == "🏠 Cotidiano":
        await send_message(
            token,
            chat_id,
            "🏠 Cotidiano. Tarefas, compromissos, rotinas, metas, lista para depois e o que está faltando em casa.",
            reply_markup=_kb(COTIDIANO_KB),
        )
        return True

    if text == "➕ Adicionar":
        await send_message(token, chat_id, "O que vamos adicionar?", reply_markup=_kb(ADD_KB))
        return True

    uid = await _uid(db, chat_id)
    if not uid:
        return False

    # Fontes autoritativas: esses botões não passam por parser informal.
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

    # Rotinas mais usadas entram direto no handler especializado, sem percorrer o dispatcher inteiro.
    if text in ROUTINE_DIRECT_BUTTONS:
        return await runtime_guard.handle_pre_dispatch(db, token, message)

    return False
