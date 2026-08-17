from telegram.ext import MessageHandler, filters

from src.natural_handlers import natural_followup


def register_pending_followup_guard(application) -> None:
    """Prioriza respostas curtas de continuação, como 'Hoje', antes de fallbacks genéricos."""
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, natural_followup),
        group=-30,
    )
