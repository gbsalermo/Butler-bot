"""Fast path determinístico para frases informais do núcleo do Butler.

Não é NLU geral: só reconhece pedidos operacionais explícitos de tarefa e
compromisso. A família linguística vem de ``language_primitives``; este módulo
continua sendo autoridade da persistência desses dois domínios.
"""

import re
from datetime import datetime, timedelta, timezone

import app
import language_primitives as language
from nlu import parse_date, parse_time, validate_future
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))


def _norm(text):
    return language.normalize_text(language.strip_butler(text), keep_temporal=True)


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
            r"^(?:butler[,!:\-]?\s*)?(?:cria|crie|criar|faz|faça|faca|fazer|anota|anote|anotar|bota|botar|coloca|coloque|colocar|marca|marque|marcar|adiciona|adicione|adicionar)\s+(?:ai\s+|aí\s+)?(?:pra mim\s+|para mim\s+)?(?:como\s+)?(?:uma\s+)?tarefa\s*(?:de\s+)?",
            r"^(?:butler[,!:\-]?\s*)?(?:nova tarefa|tarefa)\s*[:\-]?\s*",
        ]
    else:
        patterns = [
            r"^(?:butler[,!:\-]?\s*)?(?:tenho|vou ter|vai ter)\s+(?:um\s+|uma\s+)?(?:compromisso\s+(?:de\s+|com\s+)?)?",
            r"^(?:butler[,!:\-]?\s*)?(?:cria|crie|criar|faz|faça|faca|fazer|marca|marque|marcar|anota|anote|anotar|bota|botar|coloca|coloque|colocar|agenda|agende|agendar|adiciona|adicione|adicionar)\s+(?:ai\s+|aí\s+)?(?:pra mim\s+|para mim\s+)?(?:um\s+|uma\s+)?compromisso\s*(?:de\s+|com\s+)?",
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

    families = set(language.detect_action_families(text))

    # Lembretes pertencem ao parser especializado e respeitam polaridade.
    if "reminder" in families:
        return "lembrete" if language.is_positive_action_request(text, "reminder") else None

    if "create_task" in families:
        return "tarefa"
    if "create_appointment" in families:
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
