from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.database import get_user, set_preferred_name, upsert_user
from src.ui_layout import MAIN_KEYBOARD

ASK_NAME = 700
CANCEL_KEYBOARD = ReplyKeyboardMarkup([["❌ Cancelar ação"]], resize_keyboard=True)


async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_chat or not update.effective_user:
        return ConversationHandler.END

    user = update.effective_user
    chat_id = update.effective_chat.id
    upsert_user(chat_id, user.id, user.first_name, user.username)
    row = get_user(chat_id)

    if row and row["preferred_name"]:
        await update.message.reply_text(
            f"Fala daí, {row['preferred_name']}. Butler na escuta. O que precisamos organizar?",
            reply_markup=MAIN_KEYBOARD,
        )
        raise ApplicationHandlerStop

    context.user_data["onboarding_chat_id"] = chat_id
    await update.message.reply_text(
        "Antes de começarmos: como você quer que eu te chame?\n\nPode ser seu nome, apelido, `chefe` ou qualquer coisa que não me faça passar vergonha em público.",
        reply_markup=CANCEL_KEYBOARD,
    )
    return ASK_NAME


async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    chat_id = int(context.user_data.pop("onboarding_chat_id", update.effective_chat.id))

    if value == "❌ Cancelar ação":
        value = update.effective_user.first_name or "chefe"

    if len(value) < 2 or len(value) > 40:
        await update.message.reply_text("Me dê um nome/apelido entre 2 e 40 caracteres.", reply_markup=CANCEL_KEYBOARD)
        context.user_data["onboarding_chat_id"] = chat_id
        return ASK_NAME

    set_preferred_name(chat_id, value)
    await update.message.reply_text(
        f"Fechado, {value}. Vou lembrar disso. Agora sim: o que vamos colocar em ordem?",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def change_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.effective_chat:
        return ConversationHandler.END
    context.user_data["onboarding_chat_id"] = update.effective_chat.id
    await update.message.reply_text("Como quer que eu te chame daqui pra frente?", reply_markup=CANCEL_KEYBOARD)
    return ASK_NAME


def register_onboarding(application) -> None:
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_onboarding),
            MessageHandler(filters.Regex(r"^👤 Como me chamar$"), change_name_start),
        ],
        states={ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)]},
        fallbacks=[],
    )
    application.add_handler(conv, group=-20)
