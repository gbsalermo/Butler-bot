"""Configuração do runtime LEGADO de polling/SQLite.

Produção Cloudflare não importa este arquivo. O Worker usa
``cloudflare/src/settings.py`` + secrets/bindings do ambiente Cloudflare.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Token usado somente pelos entrypoints de polling em src/main*.py.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BUTLER_TIMEZONE = os.getenv("BUTLER_TIMEZONE", "America/Bahia").strip()
BUTLER_VARIANT = os.getenv("BUTLER_VARIANT", "personal").strip().lower()
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/butler.db"))

if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = BASE_DIR / DATABASE_PATH


def validate_config() -> None:
    """Falha cedo quando o processo legado inicia sem token."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN não configurado. Copie .env.example para .env e informe o token do BotFather."
        )
