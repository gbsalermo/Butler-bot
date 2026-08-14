import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BUTLER_TIMEZONE = os.getenv("BUTLER_TIMEZONE", "America/Bahia").strip()
BUTLER_VARIANT = os.getenv("BUTLER_VARIANT", "personal").strip().lower()
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/butler.db"))

if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = BASE_DIR / DATABASE_PATH


def validate_config() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN não configurado. Copie .env.example para .env e informe o token do BotFather."
        )
