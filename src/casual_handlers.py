from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from src.assistant_state import is_day_off
from src.context_engine import context_comment, daily_context
from src.database import preferred_name
from src.personality import choose, day_flavor, everyday_tone


def _normalized(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _address(text: str, chat_id: int) -> str:
    return text.replace("chefe", preferred_name(chat_id))


async def casual_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return
    text = _normalized(update.message.text or "")
    if not text or is_day_off():
        return

    greetings = {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e ai", "e aí", "fala butler", "butler"}
    thanks = {"obrigado", "valeu", "vlw", "brigado", "obg", "obrigado butler", "valeu butler"}

    if text in greetings:
        msg = choose("greeting", everyday_tone())
        flavor = day_flavor()
        comment = context_comment(daily_context())
        if flavor:
            msg += f"\n\n{flavor}"
        if comment:
            msg += f"\n\n{comment}"
        await update.message.reply_text(_address(msg, update.effective_chat.id))
        return

    if text in thanks:
        await update.message.reply_text(_address(choose("thanks", everyday_tone()), update.effective_chat.id))
        return


def register_casual_handlers(application) -> None:
    application.add_handler(
        MessageHandler(
            filters.Regex(r"(?i)^(oi|olá|ola|bom dia|boa tarde|boa noite|e aí|e ai|fala butler|butler|obrigado|valeu|vlw|brigado|obg|obrigado butler|valeu butler)$"),
            casual_reply,
        ),
        group=20,
    )
