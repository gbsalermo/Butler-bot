from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

from src.ui_layout import COTIDIANO_KEYBOARD


ADD_KEYBOARD = ReplyKeyboardMarkup(
    [["✅ Nova tarefa", "📅 Novo compromisso"], ["❌ Cancelar ação"]],
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
    application.add_handler(
        MessageHandler(filters.Regex(r"^(📌 Pendências|➕ Nova pendência)$"), old_pending_button),
        group=-18,
    )
