import logging

from telegram.ext import ApplicationBuilder

from src.bot_handlers import register_handlers
from src.config import TELEGRAM_BOT_TOKEN, validate_config
from src.database import init_database, seed_default_schedule


def main() -> None:
    validate_config()
    init_database()
    seed_default_schedule()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    register_handlers(application)

    print("Butler iniciado em polling. Pressione Ctrl+C para encerrar.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
