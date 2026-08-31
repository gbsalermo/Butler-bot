"""Sinais linguísticos de tempo relativo para o Assistente Geral de Tempo.

Este módulo continua puro: reconhece pedidos de cronômetro/alerta rápido e
converte expressões relativas em duração determinística, sem acessar D1 nem
executar a ação.
"""

from __future__ import annotations

import re

import language_primitives as language


_TIMER_PATTERNS = (
    r"^(?:cronometra|cronometre|cronometrar)\b",
    r"^(?:inicia|inicie|iniciar|comeca|comece|comecar)\b.*\b(?:cronometro|timer)\b",
    r"^(?:marca|marque|marcar)\b.*\b(?:cronometro|timer)\b",
    r"^(?:faz|faca|fazer)\b.*\b(?:cronometro|timer)\b",
)

_RELATIVE_RE = re.compile(
    r"\b(?:daqui\s+a|em)\s+(\d+)\s*(segundo|segundos|seg|minuto|minutos|min|hora|horas|h)\b"
)

_DURATION_RE = re.compile(
    r"\b(\d+)\s*(segundo|segundos|seg|minuto|minutos|min|hora|horas|h)\b"
)


def is_timer_request(text: str | None) -> bool:
    normalized = language.normalize_text(language.strip_butler(text))
    return any(re.search(pattern, normalized) for pattern in _TIMER_PATTERNS)


def _to_seconds(amount: int, unit: str) -> int:
    if unit in {"hora", "horas", "h"}:
        return amount * 3600
    if unit in {"minuto", "minutos", "min"}:
        return amount * 60
    return amount


def parse_relative_delay_seconds(text: str | None) -> int | None:
    """Extrai apenas delay explicitamente relativo: `daqui a 5 min`, `em 1 hora`."""
    normalized = language.normalize_text(language.strip_butler(text))
    match = _RELATIVE_RE.search(normalized)
    if not match:
        return None
    return _to_seconds(int(match.group(1)), match.group(2))


def parse_timer_duration_seconds(text: str | None) -> int | None:
    """Para cronômetros explícitos aceita também `cronometra 30 minutos`."""
    relative = parse_relative_delay_seconds(text)
    if relative is not None:
        return relative
    if not is_timer_request(text):
        return None
    normalized = language.normalize_text(language.strip_butler(text))
    match = _DURATION_RE.search(normalized)
    if not match:
        return None
    return _to_seconds(int(match.group(1)), match.group(2))


def classify_quick_time_intent(text: str | None) -> dict:
    """Classifica a intenção temporal sem persistência.

    `timer`: cronômetro puro.
    `relative_alert`: lembrete/tarefa verbal positiva com prazo relativo curto.
    `None`: não é assunto do assistente rápido.
    """
    duration = parse_timer_duration_seconds(text)
    if duration is not None and is_timer_request(text):
        return {"kind": "timer", "delay_seconds": duration}

    delay = parse_relative_delay_seconds(text)
    if delay is None:
        return {"kind": None, "delay_seconds": None}

    families = set(language.detect_action_families(text))
    if "reminder" in families and language.is_positive_action_request(text, "reminder"):
        return {"kind": "relative_alert", "delay_seconds": delay}
    if "create_task" in families and language.action_polarity(text, "create_task") != "negative":
        return {"kind": "relative_alert", "delay_seconds": delay}

    return {"kind": None, "delay_seconds": delay}
