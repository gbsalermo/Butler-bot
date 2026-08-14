import random

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

from src.ui_layout import COTIDIANO_KEYBOARD


COTIDIANO_LINES = [
    "Aqui ficam as pequenas coisas que costumam virar problema justamente porque ninguém lembra delas.",
    "Casa, metas, rotinas e dinheiro. A gloriosa administração da vida adulta.",
    "A área onde eu tento impedir que você descubra que acabou o café só quando já está sem café.",
    "Cotidiano, chefe. Porque aparentemente existir também exige gerenciamento de projeto.",
]


async def cotidiano(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        f"🏠 *Cotidiano*\n\n{random.choice(COTIDIANO_LINES)}",
        parse_mode="Markdown",
        reply_markup=COTIDIANO_KEYBOARD,
    )
    raise ApplicationHandlerStop


def register_personality_navigation(application) -> None:
    application.add_handler(
        MessageHandler(filters.Regex(r"^(🏠 Cotidiano|⬅️ Voltar ao cotidiano)$"), cotidiano),
        group=-6,
    )
