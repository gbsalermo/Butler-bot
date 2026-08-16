import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

from settings import OWNER_CHAT_ID, UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))

NEGATIVE_MARKERS = (
    "desanimado", "desanimada", "cansado", "cansada", "pra baixo", "para baixo",
    "sem vontade", "sem animo", "sem ânimo", "frustrado", "frustrada", "mal hoje",
    "dia ruim", "to mal", "tô mal", "nao to bem", "não tô bem", "não estou bem",
)
POSITIVE_MARKERS = (
    "hoje foi bom", "dia foi bom", "to feliz", "tô feliz", "deu certo", "consegui",
    "mandei bem", "foi massa", "foi tranquilo", "to bem", "tô bem",
)
GREETING_MARKERS = (
    "oi", "ola", "olá", "e ai", "e aí", "fala", "opa", "salve", "bom dia",
    "boa tarde", "boa noite",
)
CONTINUATION_MARKERS = (
    "sei la", "sei lá", "mais ou menos", "é", "eh", "acho que sim", "acho que nao",
    "acho que não", "talvez", "isso", "pois é", "poise",
)


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip()


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


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


def _period_phrase(now):
    if now.hour < 12:
        return "manhã"
    if now.hour < 18:
        return "tarde"
    if now.hour < 23:
        return "noite"
    return "madrugada"


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


async def _remember_state(db, uid, mood):
    detail = '{"kind":"companion","mood":"%s"}' % mood
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'conversation_state',?)").bind(uid, detail).run()


async def _last_state(db, uid):
    row = await db.prepare("SELECT detail FROM natural_events WHERE user_id=? AND event_type='conversation_state' ORDER BY id DESC LIMIT 1").bind(uid).first()
    if not row:
        return None
    detail = _row(row, "detail") or ""
    m = re.search(r'"mood":"([^"]+)"', detail)
    return m.group(1) if m else None


async def _recent_context(db, uid):
    now = _now()
    today = now.date()
    seven_days_ago = today - timedelta(days=6)

    done_row = await db.prepare(
        "SELECT COUNT(*) n FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='concluido' AND completed_at>=?"
    ).bind(uid, seven_days_ago.isoformat()).first()
    done = int(_row(done_row, "n", 0))

    overdue = await _rows(db.prepare(
        "SELECT title,due_date FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente' AND due_date<? ORDER BY due_date LIMIT 2"
    ).bind(uid, today.isoformat()))

    next_item = await db.prepare(
        "SELECT kind,title,due_date,due_time FROM daily_items WHERE user_id=? AND status='pendente' AND due_date>=? ORDER BY due_date,COALESCE(due_time,'23:59') LIMIT 1"
    ).bind(uid, today.isoformat()).first()

    workout = await db.prepare(
        "SELECT COUNT(*) n FROM workout_logs WHERE user_id=? AND workout_date>=? AND status='feito'"
    ).bind(uid, seven_days_ago.isoformat()).first()
    workouts = int(_row(workout, "n", 0))

    goals = await db.prepare(
        "SELECT COUNT(*) n FROM goal_progress gp JOIN goals g ON g.id=gp.goal_id WHERE g.user_id=? AND gp.log_date>=?"
    ).bind(uid, seven_days_ago.isoformat()).first()
    goal_hits = int(_row(goals, "n", 0))

    return {
        "done": done,
        "overdue": overdue,
        "next": next_item,
        "workouts": workouts,
        "goal_hits": goal_hits,
    }


def _is_greeting(n):
    if len(n) > 40:
        return False
    stripped = re.sub(r"\bbutler\b", "", n).strip(" ,.!?")
    return any(stripped == _norm(x) or stripped.startswith(_norm(x) + " ") for x in GREETING_MARKERS)


def _contains_any(n, markers):
    return any(_norm(x) in n for x in markers)


async def _reply_greeting(token, chat_id):
    now = _now()
    period = _period_phrase(now)
    if period == "madrugada":
        text = "Fala daí, chefe. Aconteceu alguma coisa ou a madrugada só resolveu render conversa?"
    elif period == "noite":
        text = "Fala daí, chefe. Tudo certo por aí ou apareceu alguma coisa?"
    elif period == "manhã":
        text = "Bom dia, chefe. Tudo certo por aí?"
    else:
        text = "Opa, chefe. Tudo certo por aí?"
    await send_message(token, chat_id, text)


async def _reply_negative(db, token, chat_id, uid):
    await _remember_state(db, uid, "down")
    await send_message(
        token,
        chat_id,
        "Ih. Quer falar do que pegou ou é daqueles dias em que tudo só ficou meio sem graça?",
    )


async def _reply_positive(db, token, chat_id, uid):
    await _remember_state(db, uid, "up")
    await send_message(
        token,
        chat_id,
        "Aí sim. Aconteceu alguma coisa em particular ou hoje só resolveu colaborar mesmo?",
    )


async def _reply_continuation(db, token, chat_id, uid, mood):
    ctx = await _recent_context(db, uid)
    if mood == "down":
        facts = []
        if ctx["done"]:
            facts.append(f"você concluiu {ctx['done']} tarefa(s) nos últimos dias")
        if ctx["workouts"]:
            facts.append(f"treinou {ctx['workouts']} vez(es) nesta última semana")
        if ctx["goal_hits"]:
            facts.append(f"registrou {ctx['goal_hits']} avanço(s) nas suas metas")

        if facts:
            base = "; ".join(facts[:2])
            text = f"Então eu vou te lembrar de uma coisa concreta: {base}. Tá tudo redondo? Não. Mas parado você definitivamente não tá."
        else:
            text = "Então não precisa forçar uma explicação bonita agora. Dia ruim existe. O importante é não transformar uma noite torta em sentença sobre a semana inteira."

        if ctx["next"]:
            title = _row(ctx["next"], "title")
            due_date = _row(ctx["next"], "due_date")
            due_time = _row(ctx["next"], "due_time")
            suffix = f" às {due_time}" if due_time else ""
            text += f" E a próxima coisa concreta que eu tenho aqui é {title}, em {due_date}{suffix}. Um problema por vez já tá de bom tamanho."
        await send_message(token, chat_id, text)
        return

    if mood == "up":
        text = "Bom. Guarda esse dia na memória também, porque a cabeça costuma arquivar desastre com muito mais capricho do que acerto."
        if ctx["done"]:
            text += f" E os dados ajudam: já foram {ctx['done']} tarefa(s) concluída(s) nos últimos dias."
        await send_message(token, chat_id, text)


async def handle_message(db, token, message):
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None or OWNER_CHAT_ID is None or int(chat_id) != int(OWNER_CHAT_ID):
        return False

    uid = await _uid(db, int(chat_id))
    if not uid:
        return False

    text = (message.get("text") or "").strip()
    if not text:
        return False
    n = _norm(text)

    if _is_greeting(n):
        await _reply_greeting(token, int(chat_id))
        return True

    if _contains_any(n, NEGATIVE_MARKERS):
        await _reply_negative(db, token, int(chat_id), uid)
        return True

    if _contains_any(n, POSITIVE_MARKERS):
        await _reply_positive(db, token, int(chat_id), uid)
        return True

    if _contains_any(n, CONTINUATION_MARKERS):
        mood = await _last_state(db, uid)
        if mood in ("down", "up"):
            await _reply_continuation(db, token, int(chat_id), uid, mood)
            return True

    return False
