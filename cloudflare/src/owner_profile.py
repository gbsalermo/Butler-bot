from settings import OWNER_CHAT_ID, OWNER_PREFERRED_NAME

# Dados pessoais só devem ser associados quando o chat_id recebido for exatamente OWNER_CHAT_ID.
# Usuários comuns começam sem grade e sem protocolo pessoal.

OWNER_SUBJECTS = [
    {"name": "Álgebra Linear I", "weekday": "terça-feira", "start": "10:00", "end": "12:00", "location": "PAV III, Sala 10"},
    {"name": "Álgebra Linear I", "weekday": "quinta-feira", "start": "10:00", "end": "12:00", "location": "PAV III, Sala 10"},
    {"name": "Física II", "weekday": "segunda-feira", "start": "10:00", "end": "12:00", "location": "PAV III, Sala 07"},
    {"name": "Física II", "weekday": "quarta-feira", "start": "10:00", "end": "12:00", "location": "PAV III, Sala 07"},
    {"name": "Laboratório de Sistemas Digitais I", "weekday": "segunda-feira", "start": "14:00", "end": "16:00", "location": "PAV Eng., Sala D6"},
    {"name": "Princípios de Eletrônica Analógica", "weekday": "terça-feira", "start": "08:00", "end": "10:00", "location": "PAV I, Sala 104"},
    {"name": "Princípios de Eletrônica Analógica", "weekday": "quinta-feira", "start": "08:00", "end": "10:00", "location": "PAV I, Sala 104"},
    {"name": "Sistemas Digitais I", "weekday": "segunda-feira", "start": "08:00", "end": "10:00", "location": "PAV I, Sala 11"},
    {"name": "Sistemas Digitais I", "weekday": "quarta-feira", "start": "08:00", "end": "10:00", "location": "PAV I, Sala 114"},
]

# Chaves sem acentos porque categorias informadas pelo usuário são normalizadas antes de persistir.
DEFAULT_FINANCE_LIMITS = {
    "alimentacao": 450.0,
    "lazer": 200.0,
    "transporte": 180.0,
    "compras": 250.0,
}


def is_owner(chat_id: int) -> bool:
    return OWNER_CHAT_ID is not None and int(chat_id) == int(OWNER_CHAT_ID)


def preferred_name_for(chat_id: int, telegram_first_name: str | None = None) -> str:
    if is_owner(chat_id):
        return OWNER_PREFERRED_NAME
    return (telegram_first_name or "chefe").strip()
