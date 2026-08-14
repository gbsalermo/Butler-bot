import logging

from telegram.ext import ApplicationBuilder

from src.academic_navigation import register_academic_navigation
from src.assistant_state import init_assistant_state
from src.assistant_views import register_assistant_views
from src.bot_handlers import register_handlers
from src.casual_handlers import register_casual_handlers
from src.config import TELEGRAM_BOT_TOKEN, validate_config
from src.daily_store import init_daily_store
from src.database import init_database, seed_default_schedule
from src.home_handlers import register_home_handlers
from src.home_menu import register_home_menu
from src.home_store import init_home_tables
from src.lifestyle_handlers import register_lifestyle_handlers
from src.protocol_mass_handlers import register_protocol_mass_handlers
from src.protocol_mass_navigation import register_protocol_mass_navigation
from src.protocol_mass_series import register_protocol_mass_series
from src.protocol_mass_store import init_protocol_mass_tables
from src.protocol_mass_ui import register_protocol_mass_ui
from src.scheduler import register_scheduler
from src.wellbeing_handlers import register_wellbeing_handlers


def main() -> None:
    validate_config()
    init_database()
    init_daily_store()
    init_home_tables()
    init_assistant_state()
    init_protocol_mass_tables()
    seed_default_schedule()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    register_wellbeing_handlers(application)
    register_home_menu(application)
    register_protocol_mass_series(application)
    register_protocol_mass_ui(application)
    register_protocol_mass_navigation(application)
    register_protocol_mass_handlers(application)
    register_academic_navigation(application)
    register_assistant_views(application)
    register_lifestyle_handlers(application)
    register_home_handlers(application)
    register_handlers(application)
    register_casual_handlers(application)
    register_scheduler(application)

    print("Butler iniciado em polling. Quando você descansar, ele descansa também.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
