from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, CommandHandler, ContextTypes, MessageHandler, filters

from src.assistant_state import is_day_off
from src.database import upsert_user
from src.personality import choose, day_flavor, everyday_tone
from src.ui_layout import FINANCE_KEYBOARD, MAIN_KEYBOARD

ACADEMIC_KEYBOARD = ReplyKeyboardMarkup(
    [["📚 Minhas matérias", "⚙️ Gerenciar matérias"], ["🏠 Menu principal"]], resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    user = update.effective_user
    upsert_user(update.effective_chat.id, user.id, user.first_name, user.username)
    if is_day_off():
        await update.message.reply_text(
            "🌙 Ainda estamos de folga, chefe. Eu estava conseguindo ficar quieto surpreendentemente bem.\n\n"
            "Se quiser voltar à rotina, diga *Butler, preciso de você!*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🕴️ Butler, preciso de você!"]], resize_keyboard=True),
        )
    else:
        tone = everyday_tone()
        intro = choose("wake", tone)
        flavor = day_flavor()
        if flavor:
            intro += f"\n\n{flavor}"
        await update.message.reply_text(
            f"🕴️ *Butler à disposição.*\n\n{intro}",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD,
        )
    raise ApplicationHandlerStop


async def home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        lines = [choose("wake", everyday_tone())]
        flavor = day_flavor()
        if flavor:
            lines.append(flavor)
        await update.message.reply_text("\n\n".join(lines), reply_markup=MAIN_KEYBOARD)
    raise ApplicationHandlerStop


async def academic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    extras = [
        "Sua grade e seus horários. A parte da vida em que até o caos vem com sala marcada.",
        "Grade, horários e matérias. Pelo menos alguém aqui precisa lembrar onde você deveria estar.",
        "Sua vida acadêmica, devidamente catalogada para reduzir a quantidade de 'eu tinha aula hoje?'.",
    ]
    import random
    await update.message.reply_text(
        f"📚 *Acadêmico*\n\n{random.choice(extras)}",
        parse_mode="Markdown",
        reply_markup=ACADEMIC_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def finance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "💰 *Finanças*\n\n"
        "Essa área ainda está em construção. Por enquanto eu observo de longe antes de começar a julgar seus gastos com propriedade.",
        parse_mode="Markdown",
        reply_markup=FINANCE_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def finance_placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "💰 Ainda não estou movimentando registros financeiros. Aproveite esse breve período em que suas compras não têm testemunha oficial.",
        reply_markup=FINANCE_KEYBOARD,
    )
    raise ApplicationHandlerStop


def register_home_menu(application) -> None:
    application.add_handler(CommandHandler("start", start), group=-5)
    application.add_handler(CommandHandler("menu", home), group=-5)
    application.add_handler(MessageHandler(filters.Regex(r"^🏠 Menu principal$"), home), group=-5)
    application.add_handler(MessageHandler(filters.Regex(r"^📚 Matérias$"), academic), group=-5)
    application.add_handler(MessageHandler(filters.Regex(r"^💰 Finanças$"), finance), group=-5)
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(➕ Entrada|➖ Gasto|📊 Resumo do mês|🎯 Metas financeiras|📈 Histórico)$"),
            finance_placeholder,
        ),
        group=-5,
    )
