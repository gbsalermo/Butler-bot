from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

from src.home_store import list_missing_groceries
from src.ui_layout import COTIDIANO_KEYBOARD, MAIN_KEYBOARD


ADD_KEYBOARD = ReplyKeyboardMarkup(
    [["✅ Nova tarefa", "📅 Novo compromisso"], ["❌ Cancelar ação"]],
    resize_keyboard=True,
)

GROCERY_KEYBOARD = ReplyKeyboardMarkup(
    [["➕ Adicionar item", "📋 Ver itens faltando"]],
    resize_keyboard=True,
)


async def add_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "O que entrou na agenda, chefe?",
        reply_markup=ADD_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def grocery_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "🛒 O que fazemos com a lista?",
        reply_markup=GROCERY_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def grocery_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    rows = list_missing_groceries()
    if not rows:
        text = "🛒 Não tem nada marcado como faltando. Milagre doméstico temporariamente confirmado."
    else:
        parts = ["🛒 *Está faltando:*", ""]
        for row in rows:
            quantity = f" — {row['quantity']}" if row["quantity"] else ""
            parts.append(f"• {row['name']}{quantity}")
        text = "\n".join(parts)

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    raise ApplicationHandlerStop


async def old_pending_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "📌 Pendência agora é automática: tarefa que venceu e ainda não foi concluída.\n\n"
        "Para criar algo novo, use *➕ Adicionar*. As tarefas vencidas aparecem em *🗓️ Hoje*.",
        parse_mode="Markdown",
        reply_markup=COTIDIANO_KEYBOARD,
    )
    raise ApplicationHandlerStop


def register_quick_access(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(r"^➕ Adicionar$"), add_menu), group=-18)
    application.add_handler(MessageHandler(filters.Regex(r"^🛒 Item faltando$"), grocery_menu), group=-18)
    application.add_handler(MessageHandler(filters.Regex(r"^📋 Ver itens faltando$"), grocery_list), group=-18)
    application.add_handler(
        MessageHandler(filters.Regex(r"^(📌 Pendências|➕ Nova pendência)$"), old_pending_button),
        group=-18,
    )
