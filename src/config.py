import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/butler.db"))
