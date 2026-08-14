import logging
import os

from dotenv import load_dotenv

# A versão genérica usa credenciais e banco próprios.
# O arquivo .env.generic não deve conter dados do Butler pessoal.
load_dotenv(".env.generic", override=True)
os.environ.setdefault("DATABASE_PATH", "data/butler_generic.db")

from telegram.ext import ApplicationBuilder

from src.academic_navigation import register_academic_navigation
from src.assistant_state import init_assistant_state
from src.assistant_views import register_assistant_views
from src.bot_handlers import register_handlers
from src.casual_handlers import register_casual_handlers
from src.config import TELEGRAM_BOT_TOKEN, validate_config
from src.daily_store import init_daily_store
from src.database import init_database
from src.home_handlers import register_home_handlers
from src.home_menu import register_home_menu
from src.home_store import init_home_tables
from src.lifestyle_handlers import register_lifestyle_handlers
from src.onboarding import register_onboarding
from src.personality_navigation import register_personality_navigation
from src.schedule_import_handlers import register_schedule_import
from src.scheduler import register_scheduler
from src.ui_layout import apply_layout_overrides
from src.wellbeing_handlers import register_wellbeing_handlers


def main() -> None:
    validate_config()
    init_database()
    init_daily_store()
    init_home_tables()
    init_assistant_state()
    # IMPORTANTE: sem seed_default_schedule() e sem Protocol Mass.
    apply_layout_overrides()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    register_onboarding(application)
    register_schedule_import(application)
    register_wellbeing_handlers(application)
    register_personality_navigation(application)
    register_home_menu(application)
    register_academic_navigation(application)
    register_assistant_views(application)
    register_lifestyle_handlers(application)
    register_home_handlers(application)
    register_handlers(application)
    register_casual_handlers(application)
    register_scheduler(application)

    print("Butler genérico iniciado em polling, sem dados pessoais pré-carregados.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
