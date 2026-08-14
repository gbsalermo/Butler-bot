from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

from src.home_handlers import cotidiano_menu
from src.protocol_mass_handlers import protocol_menu


async def open_protocol_mass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await protocol_menu(update, context)
    raise ApplicationHandlerStop


async def back_to_everyday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cotidiano_menu(update, context)
    raise ApplicationHandlerStop


def register_protocol_mass_navigation(application) -> None:
    application.add_handler(
        MessageHandler(filters.Regex(r"^🏋️ Musculação$"), open_protocol_mass),
        group=-3,
    )
    application.add_handler(
        MessageHandler(filters.Regex(r"^⬅️ Voltar à musculação$"), back_to_everyday),
        group=-3,
    )
