from telegram import ReplyKeyboardMarkup


MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🌙 Day-off"],
        ["➕ Adicionar", "🗓️ Hoje"],
        ["🛒 Item faltando", "📚 Matérias"],
        ["🏠 Cotidiano", "🏋️ Musculação"],
    ],
    resize_keyboard=True,
)

COTIDIANO_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["✅ Tarefas", "📅 Compromissos"],
        ["🛒 O que está faltando?", "➕ Item faltando"],
        ["📌 Ler/ver depois", "🎯 Metas"],
        ["🧘 Rotinas", "💰 Finanças"],
        ["👤 Como me chamar"],
        ["🏠 Menu principal"],
    ],
    resize_keyboard=True,
)

ACADEMIC_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📚 Minhas matérias", "⚙️ Gerenciar matérias"],
        ["📥 Importar grade por PDF/texto"],
        ["🏠 Menu principal"],
    ],
    resize_keyboard=True,
)

FINANCE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["➕ Entrada", "➖ Gasto"],
        ["📊 Resumo do mês", "🎯 Metas financeiras"],
        ["📈 Histórico"],
        ["⬅️ Voltar ao cotidiano"],
    ],
    resize_keyboard=True,
)


def apply_layout_overrides() -> None:
    """Mantém um único desenho de menus mesmo em módulos antigos."""
    import src.academic_navigation as academic_navigation
    import src.home_handlers as home_handlers
    import src.home_menu as home_menu
    import src.lifestyle_handlers as lifestyle_handlers
    import src.wellbeing_handlers as wellbeing_handlers

    home_menu.MAIN_KEYBOARD = MAIN_KEYBOARD
    home_menu.FINANCE_KEYBOARD = FINANCE_KEYBOARD
    home_menu.ACADEMIC_KEYBOARD = ACADEMIC_KEYBOARD
    academic_navigation.ACADEMIC_KEYBOARD = ACADEMIC_KEYBOARD

    lifestyle_handlers.MAIN_KEYBOARD = MAIN_KEYBOARD

    wellbeing_handlers.MAIN_KEYBOARD = MAIN_KEYBOARD
    wellbeing_handlers.HOME_KEYBOARD = COTIDIANO_KEYBOARD

    home_handlers.HOME_KEYBOARD = COTIDIANO_KEYBOARD
