"""Menus enxutos do Butler operacional.

Mantém dados/funcionalidades antigas no repositório, mas a interface de produção
prioriza apenas os núcleos do assistente cotidiano.
"""

import app
import runtime_guard
import goal_operational
from telegram_api import send_message


MAIN_KB = [
    ["🌙 Day-off"],
    ["➕ Adicionar", "🗓️ Hoje"],
    ["🛒 Item faltando", "📚 Matérias"],
    ["🏠 Cotidiano", "🏋️ Musculação"],
]

COTIDIANO_KB = [
    ["✅ Tarefas", "📅 Compromissos"],
    ["🧘 Rotinas", "🎯 Metas"],
    ["🛒 O que está faltando?", "➕ Item faltando"],
    ["👤 Como me chamar", "🏠 Menu principal"],
]

ADD_KB = [
    ["✅ Tarefa", "📅 Compromisso"],
    ["🧘 Rotinas", "🎯 Metas"],
    ["➕ Item faltando", "🏠 Menu principal"],
]


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


def install():
    app.MAIN_KB = [list(row) for row in MAIN_KB]
    app.COTIDIANO_KB = [list(row) for row in COTIDIANO_KB]
    goal_operational.install()

    try:
        runtime_guard.MAIN_KB = [list(row) for row in MAIN_KB]
    except Exception:
        pass
    try:
        runtime_guard.COTIDIANO_KB = [list(row) for row in COTIDIANO_KB]
    except Exception:
        pass


async def handle_message(db, token, message):
    # Metas pertencem ao núcleo operacional e têm prioridade antes do menu base.
    if await goal_operational.handle_message(db, token, message):
        return True

    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False

    if text == "🏠 Cotidiano":
        await send_message(
            token,
            int(chat_id),
            "🏠 Cotidiano. Tarefas, compromissos, rotinas, metas e o que está faltando em casa. O resto não precisa disputar sua atenção.",
            reply_markup=_kb(COTIDIANO_KB),
        )
        return True

    if text == "➕ Adicionar":
        await send_message(
            token,
            int(chat_id),
            "O que vamos adicionar?",
            reply_markup=_kb(ADD_KB),
        )
        return True

    return False
