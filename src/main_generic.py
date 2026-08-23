"""Entrypoint LEGADO da variante genérica em polling + SQLite.

Este processo foi criado antes do Worker Cloudflare multiusuário atual. Ele usa
``.env.generic`` e um banco SQLite próprio; não é o perfil genérico executado em
produção.

Para mudanças no bot implantado, edite ``cloudflare/``. Este arquivo permanece
como referência/fallback histórico. Veja ``src/README.md``.
"""

import logging
import os

from dotenv import load_dotenv

# Carrega configuração específica antes de importar src.config, pois config lê
# as variáveis de ambiente no momento do import.
load_dotenv(".env.generic", override=True)
os.environ.setdefault("DATABASE_PATH", "data/butler_generic.db")
os.environ.setdefault("BUTLER_VARIANT", "generic")
os.environ.setdefault("BUTLER_MULTIUSER", "1")

from telegram.ext import ApplicationBuilder

from src.academic_navigation import register_academic_navigation
from src.assistant_views import register_assistant_views
from src.behavior_handlers import register_behavior_handlers
from src.bot_handlers import register_handlers
from src.casual_handlers import register_casual_handlers
from src.config import TELEGRAM_BOT_TOKEN, validate_config
from src.finance_handlers import register_finance_handlers
from src.history_handlers import register_history_handlers
from src.home_handlers import register_home_handlers
from src.home_menu import register_home_menu
from src.lifestyle_handlers import register_lifestyle_handlers
from src.natural_handlers import register_natural_handlers
from src.onboarding import register_onboarding
from src.personality_navigation import register_personality_navigation
from src.quick_access import register_quick_access
from src.quick_capture import register_quick_capture
from src.schedule_import_handlers import register_schedule_import
from src.scheduler import register_scheduler
from src.ui_layout import apply_layout_overrides
from src.user_scope import register_user_scope
from src.wellbeing_handlers import register_wellbeing_handlers
from src.workout_import_handlers import register_workout_import


def main():
    """Inicializa a variante genérica antiga e inicia long polling."""
    validate_config()
    apply_layout_overrides()
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Ordem histórica dos handlers deste runtime. Não use como referência da
    # prioridade do dispatcher Cloudflare atual.
    register_user_scope(application)
    register_onboarding(application)
    register_schedule_import(application)
    register_workout_import(application)
    register_wellbeing_handlers(application)
    register_quick_access(application)
    register_personality_navigation(application)
    register_finance_handlers(application)
    register_home_menu(application)
    register_academic_navigation(application)
    register_assistant_views(application)
    register_history_handlers(application)
    register_behavior_handlers(application)
    register_quick_capture(application)
    register_lifestyle_handlers(application)
    register_home_handlers(application)
    register_handlers(application)
    register_natural_handlers(application)
    register_casual_handlers(application)
    register_scheduler(application)

    print("Butler genérico iniciado em polling (runtime legado).")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
