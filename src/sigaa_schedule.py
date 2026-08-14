import re
from dataclasses import dataclass


WEEKDAY_BY_CODE = {
    "2": "segunda-feira",
    "3": "terça-feira",
    "4": "quarta-feira",
    "5": "quinta-feira",
    "6": "sexta-feira",
    "7": "sábado",
}

TURN_NAMES = {
    "M": "manhã",
    "T": "tarde",
    "N": "noite",
}

# O SIGAA exibe intervalos com minutos quebrados (08:01, 08:51, 14:01 etc.),
# mas para o Butler usamos blocos de horas completas. Isso deixa agenda,
# lembretes e importação de grade alinhados com a forma prática de consultar
# os horários: M23 = 08:00-10:00, M45 = 10:00-12:00, T23 = 14:00-16:00 etc.
SLOTS = {
    "M": {
        "1": ("07:00", "08:00"),
        "2": ("08:00", "09:00"),
        "3": ("09:00", "10:00"),
        "4": ("10:00", "11:00"),
        "5": ("11:00", "12:00"),
        "6": ("12:00", "13:00"),
    },
    "T": {
        "1": ("13:00", "14:00"),
        "2": ("14:00", "15:00"),
        "3": ("15:00", "16:00"),
        "4": ("16:00", "17:00"),
        "5": ("17:00", "18:00"),
        "6": ("18:00", "19:00"),
    },
    "N": {
        "1": ("18:00", "19:00"),
        "2": ("19:00", "20:00"),
        "3": ("20:00", "21:00"),
        "4": ("21:00", "22:00"),
        "5": ("22:00", "23:00"),
    },
}


@dataclass(frozen=True)
class ParsedSigaaSchedule:
    code: str
    weekdays: list[str]
    turn: str
    periods: list[str]
    start_time: str
    end_time: str

    @property
    def sessions(self) -> list[tuple[str, str, str]]:
        return [(day, self.start_time, self.end_time) for day in self.weekdays]

    @property
    def description(self) -> str:
        days = _join_words([day.replace("-feira", "") for day in self.weekdays])
        return f"{days}, à {TURN_NAMES[self.turn]}, das {_friendly_time(self.start_time)} às {_friendly_time(self.end_time)}"


def parse_sigaa_schedule(value: str) -> ParsedSigaaSchedule:
    code = re.sub(r"\s+", "", value.upper())
    match = re.fullmatch(r"([2-7]+)([MTN])([1-6]+)", code)
    if not match:
        raise ValueError("Código SIGAA inválido.")

    day_codes, turn, period_codes = match.groups()
    slots = SLOTS[turn]

    if any(period not in slots for period in period_codes):
        raise ValueError(f"O turno {turn} não possui um dos horários informados.")

    period_numbers = [int(period) for period in period_codes]
    if period_numbers != sorted(set(period_numbers)):
        raise ValueError("Os horários precisam estar em ordem e não podem se repetir.")

    if any(b != a + 1 for a, b in zip(period_numbers, period_numbers[1:])):
        raise ValueError("Os horários da aula precisam formar um bloco contínuo.")

    weekdays = []
    for day_code in day_codes:
        weekday = WEEKDAY_BY_CODE[day_code]
        if weekday not in weekdays:
            weekdays.append(weekday)

    first_period = period_codes[0]
    last_period = period_codes[-1]

    return ParsedSigaaSchedule(
        code=code,
        weekdays=weekdays,
        turn=turn,
        periods=list(period_codes),
        start_time=slots[first_period][0],
        end_time=slots[last_period][1],
    )


def _friendly_time(value: str) -> str:
    hour, minute = value.split(":")
    hour_int = int(hour)
    minute_int = int(minute)
    return f"{hour_int}h" if minute_int == 0 else f"{hour_int}h{minute_int:02d}"


def _join_words(words: list[str]) -> str:
    if len(words) == 1:
        return words[0]
    if len(words) == 2:
        return f"{words[0]} e {words[1]}"
    return ", ".join(words[:-1]) + f" e {words[-1]}"
