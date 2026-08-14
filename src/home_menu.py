from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, CommandHandler, ContextTypes, MessageHandler, filters

from src.database import upsert_user

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📚 Matérias", "✅ Tarefas"],
        ["📅 Compromissos", "📌 Pendências"],
        ["🏠 Cotidiano", "🗓️ Hoje"],
        ["💰 Finanças"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    user = update.effective_user
    upsert_user(update.effective_chat.id, user.id, user.first_name, user.username)
    await update.message.reply_text(
        "🕴️ *Butler à disposição.*\n\n"
        "Organizo sua vida acadêmica, tarefas, compromissos, pendências, itens de casa, metas, musculação e finanças. "
        "Também posso te avisar proativamente sobre horários importantes.\n\n"
        "Escolha uma área:",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("🕴️ Menu principal do Butler.", reply_markup=MAIN_KEYBOARD)
    raise ApplicationHandlerStop


def register_home_menu(application) -> None:
    application.add_handler(CommandHandler("start", start), group=-2)
    application.add_handler(CommandHandler("menu", home), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^🏠 Menu principal$"), home), group=-2)
