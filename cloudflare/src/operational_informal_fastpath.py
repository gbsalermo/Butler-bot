"""Fast path determinístico para frases informais do núcleo do Butler.

Não é NLU geral: só reconhece pedidos operacionais explícitos de tarefa e
compromisso. Provas e lembretes usam parsers especializados.
"""

import re
import unicodedata
from datetime import datetime, timedelta, timezone

import app
from nlu import parse_date, parse_time, validate_future
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))


def _norm(text):
    v = unicodedata.normalize("NFKD", (text or "").lower())
    v = "".join(c for c in v if not unicodedata.combining(c))
    v = re.sub(r"[^a-z0-9:/ ]+", " ", v)
    return re.sub(r"\s+", " ", v).strip()


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


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


def _clean_title(text, kind):
    value = text.strip()
    if kind == "tarefa":
        patterns = [
            r"^(?:butler[,!:\-]?\s*)?(?:eu\s+)?(?:tenho que|tenho de|preciso|preciso de|devo)\s+",
            r"^(?:butler[,!:\-]?\s*)?(?:cria|crie|faz|faça|faca|anota|anote|bota|coloca|coloque|marca|marque|adiciona|adicione)\s+(?:ai\s+|aí\s+)?(?:pra mim\s+|para mim\s+)?(?:como\s+)?(?:uma\s+)?tarefa\s*(?:de\s+)?",
            r"^(?:butler[,!:\-]?\s*)?(?:nova tarefa|tarefa)\s*[:\-]?\s*",
        ]
    else:
        patterns = [
            r"^(?:butler[,!:\-]?\s*)?(?:tenho|vou ter|vai ter)\s+(?:um\s+|uma\s+)?(?:compromisso\s+(?:de\s+|com\s+)?)?",
            r"^(?:butler[,!:\-]?\s*)?(?:cria|crie|faz|faça|faca|marca|marque|anota|anote|bota|coloca|coloque|agenda|agende|adiciona|adicione)\s+(?:ai\s+|aí\s+)?(?:pra mim\s+|para mim\s+)?(?:um\s+|uma\s+)?compromisso\s*(?:de\s+|com\s+)?",
            r"^(?:butler[,!:\-]?\s*)?(?:novo compromisso|compromisso)\s*[:\-]?\s*",
        ]
    for pattern in patterns:
        new = re.sub(pattern, "", value, flags=re.I)
        if new != value:
            value = new
            break

    value = re.sub(r"\b(?:hoje|amanhã|amanha)\b", "", value, flags=re.I)
    value = re.sub(r"\b(?:segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)(?:-feira)?\b", "", value, flags=re.I)
    value = re.sub(r"\b(?:dia\s+)?\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", "", value, flags=re.I)
    value = re.sub(r"(?:às|as)\s*\d{1,2}(?::\d{2}|h\d{0,2})?", "", value, flags=re.I)
    value = re.sub(r"\b\d{1,2}(?::\d{2}|h\d{0,2})\b", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip(" ,.-")


def classify(text):
    n = _norm(text)
    if not n:
        return None

    # Botões do Telegram nunca devem ser interpretados como texto natural.
    if n in {"tarefa", "tarefas", "compromisso", "compromissos"}:
        return None

    # Lembretes explícitos pertencem ao parser especializado.
    if re.match(r"^(?:butler\s+)?(?:me\s+)?(?:lembra|lembre|avisa|avise)\b", n):
        return "lembrete"
    if re.match(r"^(?:butler\s+)?(?:cria|crie|faz|faca|anota|coloca|adiciona)\s+(?:um\s+|uma\s+)?lembrete\b", n):
        return "lembrete"

    task_patterns = (
        r"^(?:butler\s+)?(?:eu\s+)?(?:tenho que|tenho de|preciso|devo)\b",
        r"^(?:butler\s+)?(?:cria|crie|faz|faca|anota|bota|coloca|marca|adiciona)\b.*\btarefa\b",
        r"^(?:butler\s+)?(?:nova tarefa|tarefa)\b.+",
    )
    if any(re.search(p, n) for p in task_patterns):
        return "tarefa"

    appointment_patterns = (
        r"^(?:butler\s+)?(?:cria|crie|faz|faca|marca|anota|bota|coloca|agenda|adiciona)\b.*\bcompromisso\b",
        r"^(?:butler\s+)?(?:novo compromisso|compromisso)\b.+",
        r"^(?:butler\s+)?tenho\s+(?:consulta|dentista|reuniao|entrevista|medico|medica)\b",
        r"^(?:butler\s+)?vou ter\s+(?:consulta|dentista|reuniao|entrevista|compromisso)\b",
        r"^(?:butler\s+)?(?:consulta|dentista|reuniao|entrevista|medico|medica)\b",
    )
    if any(re.search(p, n) for p in appointment_patterns):
        return "compromisso"
    return None


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    kind = classify(text)
    if kind not in ("tarefa", "compromisso"):
        return False

    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    uid = await _uid(db, int(chat_id))
    if uid is None:
        return False

    title = _clean_title(text, kind) or ("Nova tarefa" if kind == "tarefa" else "Novo compromisso")
    today = _now().date()
    due = parse_date(text, today)
    tm = parse_time(text)

    if not due:
        await app.set_state(db, uid, "item_date", {"kind": kind, "title": title})
        await send_message(
            token,
            int(chat_id),
            f"{'📝' if kind == 'tarefa' else '📅'} Entendi: {title}. Quando? Pode mandar `hoje`, `amanhã`, `sexta` ou `24/09`.",
            reply_markup={"keyboard": [["❌ Cancelar ação"]], "resize_keyboard": True},
        )
        return True

    ok, msg = validate_future(due, tm, _now().replace(tzinfo=None))
    if not ok:
        await send_message(token, int(chat_id), msg)
        return True

    row = await db.prepare(
        "INSERT INTO daily_items(user_id,kind,title,due_date,due_time,status) VALUES(?,?,?,?,?,'pendente') RETURNING id"
    ).bind(uid, kind, title, due.isoformat(), tm).first()
    iid = int(_row(row, "id"))

    try:
        import conversation_layer
        await conversation_layer._remember(db, uid, kind, iid)
    except Exception:
        pass

    when = due.strftime("%d/%m") + (f" às {tm}" if tm else "")
    await send_message(
        token,
        int(chat_id),
        f"{'📝' if kind == 'tarefa' else '📅'} Fechado: {title} — {when}.",
        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
    )
    return True
