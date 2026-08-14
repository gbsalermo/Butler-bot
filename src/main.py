import logging

from telegram.ext import ApplicationBuilder

from src.bot_handlers import register_handlers
from src.config import TELEGRAM_BOT_TOKEN, validate_config
from src.daily_store import init_daily_store
from src.database import init_database, seed_default_schedule
from src.home_handlers import register_home_handlers
from src.home_menu import register_home_menu
from src.home_store import init_home_tables
from src.lifestyle_handlers import register_lifestyle_handlers
from src.scheduler import register_scheduler


def main() -> None:
    validate_config()
    init_database()
    init_daily_store()
    init_home_tables()
    seed_default_schedule()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # O menu principal completo entra antes dos módulos específicos.
    register_home_menu(application)
    register_lifestyle_handlers(application)
    register_home_handlers(application)
    register_handlers(application)
    register_scheduler(application)

    print("Butler iniciado em polling com lembretes proativos. Pressione Ctrl+C para encerrar.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
