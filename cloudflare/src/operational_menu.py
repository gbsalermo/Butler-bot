"""Menus enxutos do Butler operacional.

Mantém dados/funcionalidades antigas no repositório, mas a interface de produção
prioriza apenas os núcleos do assistente cotidiano.
"""

import app
import runtime_guard


MAIN_KB = [
    ["🌙 Day-off"],
    ["➕ Adicionar", "🗓️ Hoje"],
    ["🛒 Item faltando", "📚 Matérias"],
    ["🏠 Cotidiano", "🏋️ Musculação"],
]

COTIDIANO_KB = [
    ["✅ Tarefas", "📅 Compromissos"],
    ["🧘 Rotinas", "🛒 O que está faltando?"],
    ["➕ Item faltando", "👤 Como me chamar"],
    ["🏠 Menu principal"],
]

ADD_KB = [
    ["✅ Tarefa", "📅 Compromisso"],
    ["🧘 Rotinas", "➕ Item faltando"],
    ["🏠 Menu principal"],
]


def install():
    app.MAIN_KB = [list(row) for row in MAIN_KB]
    app.COTIDIANO_KB = [list(row) for row in COTIDIANO_KB]

    # Alguns patches usam referências próprias aos teclados do app.
    try:
        runtime_guard.MAIN_KB = [list(row) for row in MAIN_KB]
    except Exception:
        pass
    try:
        runtime_guard.COTIDIANO_KB = [list(row) for row in COTIDIANO_KB]
    except Exception:
        pass


def add_keyboard():
    return [list(row) for row in ADD_KB]
