from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

from src.ui_layout import MAIN_KEYBOARD


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


async def cancel_add_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Certo. Nada foi adicionado.", reply_markup=MAIN_KEYBOARD)
    raise ApplicationHandlerStop


def register_quick_access(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(r"^➕ Adicionar$"), add_menu), group=-18)
    application.add_handler(MessageHandler(filters.Regex(r"^❌ Cancelar ação$"), cancel_add_menu), group=30)
