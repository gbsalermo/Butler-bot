from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, CommandHandler, ContextTypes, MessageHandler, filters

from src.assistant_state import is_day_off
from src.database import upsert_user

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🌙 Day-off"],
        ["📚 Matérias", "✅ Tarefas"],
        ["📅 Compromissos", "📌 Pendências"],
        ["🏠 Cotidiano", "🗓️ Hoje"],
        ["💰 Finanças"],
    ], resize_keyboard=True,
)

ACADEMIC_KEYBOARD = ReplyKeyboardMarkup(
    [["📚 Minhas matérias", "⚙️ Gerenciar matérias"], ["🏠 Menu principal"]], resize_keyboard=True
)
FINANCE_KEYBOARD = ReplyKeyboardMarkup(
    [["➕ Entrada", "➖ Gasto"], ["📊 Resumo do mês", "🎯 Metas financeiras"],
     ["📈 Histórico", "🏠 Menu principal"]], resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    user = update.effective_user
    upsert_user(update.effective_chat.id, user.id, user.first_name, user.username)
    if is_day_off():
        await update.message.reply_text(
            "🌙 Eu ainda estou em Day-off com você. Se quiser voltar à rotina, diga *Butler, preciso de você!*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🕴️ Butler, preciso de você!"]], resize_keyboard=True),
        )
    else:
        await update.message.reply_text(
            "🕴️ *Butler à disposição.*\n\nO que precisamos organizar agora?",
            parse_mode="Markdown", reply_markup=MAIN_KEYBOARD,
        )
    raise ApplicationHandlerStop


async def home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("🕴️ Estou aqui. O que vamos cuidar?", reply_markup=MAIN_KEYBOARD)
    raise ApplicationHandlerStop


async def academic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📚 *Acadêmico*\n\nSua grade, horários e gerenciamento das matérias ficam aqui.",
        parse_mode="Markdown", reply_markup=ACADEMIC_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def finance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "💰 *Finanças*\n\nA estrutura está reservada para entradas, gastos, histórico, comparação mensal, economia e metas. O registro financeiro será uma próxima frente do Butler.",
        parse_mode="Markdown", reply_markup=FINANCE_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def finance_placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "💰 Ainda não estou movimentando os registros financeiros nesta versão. Essa área permanece preparada para a próxima evolução.",
        reply_markup=FINANCE_KEYBOARD,
    )
    raise ApplicationHandlerStop


def register_home_menu(application) -> None:
    application.add_handler(CommandHandler("start", start), group=-5)
    application.add_handler(CommandHandler("menu", home), group=-5)
    application.add_handler(MessageHandler(filters.Regex(r"^🏠 Menu principal$"), home), group=-5)
    application.add_handler(MessageHandler(filters.Regex(r"^📚 Matérias$"), academic), group=-5)
    application.add_handler(MessageHandler(filters.Regex(r"^💰 Finanças$"), finance), group=-5)
    application.add_handler(MessageHandler(filters.Regex(r"^(➕ Entrada|➖ Gasto|📊 Resumo do mês|🎯 Metas financeiras|📈 Histórico)$"), finance_placeholder), group=-5)
