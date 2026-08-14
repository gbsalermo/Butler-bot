# Configuração pública da implantação do Butler.
# O TELEGRAM_BOT_TOKEN continua sendo o único secret obrigatório no Worker.

# Preencher com o chat_id real do proprietário antes de ativar o webhook em produção.
# Não é secret; fica público por decisão de projeto.
OWNER_CHAT_ID: int | None = None
OWNER_PREFERRED_NAME = "Gabriel"
TIMEZONE_NAME = "America/Bahia"

MORNING_SUMMARY_HOUR = 7
MORNING_SUMMARY_MINUTE = 30
WEEKLY_SUMMARY_WEEKDAY = 6  # domingo, usando 0=segunda ... 6=domingo
WEEKLY_SUMMARY_HOUR = 20
WEEKLY_SUMMARY_MINUTE = 0
