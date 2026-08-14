from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from src.assistant_state import is_day_off
from src.personality import Tone, choose, day_flavor, everyday_tone


def _normalized(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


async def casual_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = _normalized(update.message.text or "")
    if not text:
        return

    if is_day_off():
        return

    greetings = {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e ai", "e aí", "fala butler", "butler"}
    thanks = {"obrigado", "valeu", "vlw", "brigado", "obg", "obrigado butler", "valeu butler"}

    if text in greetings:
        tone = everyday_tone()
        msg = choose("greeting", tone)
        flavor = day_flavor()
        if flavor:
            msg += f"\n\n{flavor}"
        await update.message.reply_text(msg)
        return

    if text in thanks:
        await update.message.reply_text(choose("thanks", everyday_tone()))
        return


def register_casual_handlers(application) -> None:
    application.add_handler(
        MessageHandler(
            filters.Regex(r"(?i)^(oi|olá|ola|bom dia|boa tarde|boa noite|e aí|e ai|fala butler|butler|obrigado|valeu|vlw|brigado|obg|obrigado butler|valeu butler)$"),
            casual_reply,
        ),
        group=20,
    )
