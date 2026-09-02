"""Linguagem natural conservadora para criação e conclusão de rotinas."""

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


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


async def _rows(stmt):
    result = await stmt.all()
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


def _looks_like_create(text):
    n = _norm(text)
    patterns = (
        r"^(?:butler\s+)?(?:quero|preciso|gostaria de|vou)\s+(?:adicionar|criar|cadastrar|montar|colocar|botar)\s+(?:uma\s+)?rotina\b",
        r"^(?:butler\s+)?(?:cria|crie|faz|faca|monta|monte|adiciona|adicione|cadastra|cadastre|anota|anote|coloca|coloque|bota|registre|registra)\s+(?:ai\s+)?(?:uma\s+)?rotina\b",
        r"^(?:butler\s+)?(?:nova\s+)?rotina\s+(?:de\s+)?\S+",
        r"^(?:butler\s+)?(?:todo dia|todos os dias)\s+(?:quero|vou|preciso)\s+.+",
    )
    return any(re.search(pattern, n) for pattern in patterns)


def _extract_name(text):
    value = (text or "").strip()
    patterns = (
        r"^(?:Butler[,!:\-]?\s*)?(?:quero|preciso|gostaria de|vou)\s+(?:adicionar|criar|cadastrar|montar|colocar|botar)\s+(?:uma\s+)?rotina\s*(?:de\s+)?",
        r"^(?:Butler[,!:\-]?\s*)?(?:cria|crie|faz|faça|faca|monta|monte|adiciona|adicione|cadastra|cadastre|anota|anote|coloca|coloque|bota|registra|registre)\s+(?:aí\s+|ai\s+)?(?:uma\s+)?rotina\s*(?:de\s+)?",
        r"^(?:Butler[,!:\-]?\s*)?(?:nova\s+)?rotina\s*(?:de\s+)?",
        r"^(?:Butler[,!:\-]?\s*)?(?:todo dia|todos os dias)\s+(?:quero|vou|preciso)\s+",
    )
    for pattern in patterns:
        new = re.sub(pattern, "", value, flags=re.I)
        if new != value:
            value = new
            break
    value = re.split(
        r"\b(?:todos os dias|todo dia|segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo|às|as)\b|\b\d{1,2}(?::\d{2}|h\d{0,2})\b",
        value,
        maxsplit=1,
        flags=re.I,
    )[0]
    return re.sub(r"\s+", " ", value).strip(" ,.-")


_COMPLETION_PREFIX = re.compile(
    r"^(?:butler\s+)?(?:ja\s+)?(?:estudei|pratiquei|fiz|cumpri|completei|terminei|finalizei|li|meditei)\s+(?:o\s+|a\s+|meu\s+|minha\s+)?(.+)$"
)


def _completion_target(text):
    """Retorna o alvo de uma conclusão espontânea de rotina.

    `bebi água` fica deliberadamente de fora: água possui checkpoints próprios e
    não deve encerrar a rotina inteira por acidente.
    """
    match = _COMPLETION_PREFIX.match(_norm(text))
    if not match:
        return None
    target = match.group(1).strip()
    return target or None


def _looks_like_completion(text):
    return _completion_target(text) is not None


def _meaningful_tokens(value):
    generic = {
        "a", "as", "de", "do", "da", "dos", "das", "e", "o", "os",
        "meu", "minha", "rotina", "rotinas", "curso", "cursos",
        "estudo", "estudos", "estudar", "atividade", "atividades", "hoje",
    }
    return {token for token in _norm(value).split() if len(token) >= 3 and token not in generic}


def _match_routine(rows, target):
    """Resolve uma rotina ativa somente quando há um único alvo seguro."""
    target_norm = _norm(target)
    if not target_norm:
        return None, []

    direct = []
    for row in rows:
        name = _norm(_row(row, "name") or "")
        category = _norm(_row(row, "category") or "")
        fields = [field for field in (name, category) if len(field) >= 3]
        if any(target_norm == field or target_norm in field or field in target_norm for field in fields):
            direct.append(row)
    if len(direct) == 1:
        return direct[0], direct
    if len(direct) > 1:
        return None, direct

    target_tokens = _meaningful_tokens(target_norm)
    if not target_tokens:
        return None, []

    scored = []
    for row in rows:
        haystack_tokens = _meaningful_tokens(
            f"{_row(row, 'name') or ''} {_row(row, 'category') or ''}"
        )
        overlap = target_tokens & haystack_tokens
        if overlap:
            scored.append((len(overlap), row))
    if not scored:
        return None, []

    best_score = max(score for score, _ in scored)
    best = [row for score, row in scored if score == best_score]
    return (best[0] if len(best) == 1 else None), best


async def _find_completion_routine(db, uid, target):
    rows = await _rows(
        db.prepare(
            "SELECT id,name,category,time_hhmm,weekdays FROM routines WHERE user_id=? AND active=1 ORDER BY name"
        ).bind(uid)
    )
    return _match_routine(rows, target)


async def _handle_completion(db, token, chat_id, uid, text):
    target = _completion_target(text)
    if not target:
        return False

    routine, matches = await _find_completion_routine(db, uid, target)
    if routine is None:
        if len(matches) > 1:
            names = "\n".join(f"• {_row(row, 'name')}" for row in matches[:8])
            await send_message(
                token,
                int(chat_id),
                "Achei mais de uma rotina que pode ser essa. Diga o nome com um pouco mais de detalhe:\n\n" + names,
                reply_markup=_kb(CANCEL_KB),
            )
            return True
        return False

    # A persistência continua na autoridade já usada pelo domínio de rotinas.
    import academic_intelligence

    done, total = await academic_intelligence._complete_routine_all(db, uid, routine)
    await send_message(
        token,
        int(chat_id),
        f"✅ {_row(routine, 'name')} cumprida hoje: {done}/{total}. Meta contabilizada.",
        reply_markup=_kb(runtime_guard.ROUTINE_KB),
    )
    return True


async def handle_message(db, token, message):
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if chat_id is None or not text:
        return False

    uid = await runtime_guard._uid(db, int(chat_id))
    if not uid:
        return False

    if await _handle_completion(db, token, chat_id, uid, text):
        return True

    if not _looks_like_create(text):
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
