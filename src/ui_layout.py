from telegram import ReplyKeyboardMarkup


MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🌙 Day-off"],
        ["🏋️ Musculação", "📚 Matérias"],
        ["✅ Tarefas", "📅 Compromissos"],
        ["📌 Pendências", "🗓️ Hoje"],
        ["🏠 Cotidiano"],
    ],
    resize_keyboard=True,
)

COTIDIANO_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🛒 O que está faltando?", "➕ Item faltando"],
        ["🎯 Metas", "🧘 Rotinas"],
        ["💰 Finanças"],
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
    """Mantém um único desenho de menus mesmo em módulos antigos.

    Alguns handlers ainda possuem constantes locais de teclado. Em vez de duplicar
    a alteração em todos eles, substituímos essas referências na inicialização.
    """
    import src.home_handlers as home_handlers
    import src.home_menu as home_menu
    import src.lifestyle_handlers as lifestyle_handlers
    import src.wellbeing_handlers as wellbeing_handlers

    home_menu.MAIN_KEYBOARD = MAIN_KEYBOARD
    home_menu.FINANCE_KEYBOARD = FINANCE_KEYBOARD

    lifestyle_handlers.MAIN_KEYBOARD = MAIN_KEYBOARD

    wellbeing_handlers.MAIN_KEYBOARD = MAIN_KEYBOARD
    wellbeing_handlers.HOME_KEYBOARD = COTIDIANO_KEYBOARD

    home_handlers.HOME_KEYBOARD = COTIDIANO_KEYBOARD
