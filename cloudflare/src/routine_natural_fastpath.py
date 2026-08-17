"""Criação de rotina por linguagem natural sem NLU ampla.

Reconhece apenas pedidos explícitos e reaproveita o fluxo guiado do runtime_guard.
"""

import re
import unicodedata

import runtime_guard
from telegram_api import send_message

CANCEL_KB = [["❌ Cancelar ação"]]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


def _looks_like_create(text):
    n = _norm(text)
    patterns = (
        r"^(?:butler\s+)?(?:quero|preciso|gostaria de)\s+(?:adicionar|criar|cadastrar)\s+(?:uma\s+)?rotina\b",
        r"^(?:butler\s+)?(?:cria|crie|faz|faca|adiciona|adicione|cadastra|cadastre|anota|anote)\s+(?:uma\s+)?rotina\b",
        r"^(?:butler\s+)?(?:nova\s+)?rotina\s+(?:de\s+)?\S+",
    )
    return any(re.search(p, n) for p in patterns)


def _extract_name(text):
    value = (text or "").strip()
    patterns = (
        r"^(?:Butler[,!:\-]?\s*)?(?:quero|preciso|gostaria de)\s+(?:adicionar|criar|cadastrar)\s+(?:uma\s+)?rotina\s*(?:de\s+)?",
        r"^(?:Butler[,!:\-]?\s*)?(?:cria|crie|faz|faça|faca|adiciona|adicione|cadastra|cadastre|anota|anote)\s+(?:uma\s+)?rotina\s*(?:de\s+)?",
        r"^(?:Butler[,!:\-]?\s*)?(?:nova\s+)?rotina\s*(?:de\s+)?",
    )
    for p in patterns:
        new = re.sub(p, "", value, flags=re.I)
        if new != value:
            value = new
            break

    # Se a pessoa já colocou horário/dias, não usamos isso como parte do nome.
    value = re.split(
        r"\b(?:todos os dias|todo dia|segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo|às|as)\b|\b\d{1,2}(?::\d{2}|h\d{0,2})\b",
        value,
        maxsplit=1,
        flags=re.I,
    )[0]
    return re.sub(r"\s+", " ", value).strip(" ,.-")


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if chat_id is None or not text or not _looks_like_create(text):
        return False

    uid = await runtime_guard._uid(db, int(chat_id))
    if not uid:
        return False

    name = _extract_name(text)
    if not name:
        await runtime_guard._set_state(db, uid, "guard_routine_name", {})
        await send_message(
            token,
            int(chat_id),
            "🧘 Beleza. Qual é o nome da rotina? Ex.: `Estudar inglês`, `Beber água`.",
            reply_markup=_kb(CANCEL_KB),
        )
        return True

    await runtime_guard._set_state(db, uid, "guard_routine_category", {"name": name})
    await send_message(
        token,
        int(chat_id),
        f"🧘 Entendi: {name}. Essa rotina entra em qual categoria/meta?\nEx.: `Inglês`, `Água`, `Musculação` ou `Outra`.",
        reply_markup=_kb(CANCEL_KB),
    )
    return True
