"""Configuração versionada do deploy pessoal do Butler.

Este módulo NÃO contém secrets do Telegram. Valores daqui são importados por
vários schedulers/handlers e, portanto, mudar horário ou offset pode alterar o
comportamento de toda a produção.

Atenção: ``TIMEZONE_NAME`` é hoje apenas descritivo. O runtime constrói fusos
com ``UTC_OFFSET_HOURS``; não presuma que ZoneInfo esteja sendo usado.

Dados específicos do proprietário permanecem versionados porque o projeto ainda
é um assistente pessoal. Se o Butler virar produto/distribuição genérica, mover
identificação e seed pessoal para configuração privada é a direção recomendada.
"""

# Identidade do perfil pessoal. Nunca use estes valores para decidir o usuário
# de uma mensagem sem passar pela barreira ``is_owner(chat_id)``.
OWNER_CHAT_ID = 7882764998
OWNER_PREFERRED_NAME = "Gabriel"

# Fonte temporal efetiva atual: UTC_OFFSET_HOURS. TIMEZONE_NAME documenta a
# intenção geográfica, mas ainda não é consumido diretamente pelos schedulers.
TIMEZONE_NAME = "America/Bahia"
UTC_OFFSET_HOURS = -3

# Local meteorológico padrão somente para o perfil proprietário. Outros usuários
# precisam configurar explicitamente com `clima em <cidade>`.
DEFAULT_WEATHER_CITY = "Cruz das Almas - BA"
DEFAULT_WEATHER_LATITUDE = -12.667516
DEFAULT_WEATHER_LONGITUDE = -39.100787

# Resumo diário: 07:00 no horário local calculado pelo offset acima.
MORNING_SUMMARY_HOUR = 7
MORNING_SUMMARY_MINUTE = 0

# datetime.weekday(): segunda=0 ... domingo=6.
WEEKLY_SUMMARY_WEEKDAY = 6
WEEKLY_SUMMARY_HOUR = 20
WEEKLY_SUMMARY_MINUTE = 0
