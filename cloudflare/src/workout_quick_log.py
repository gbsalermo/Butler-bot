"""Registro de séries autossuficientes, seguro para reentrega do Telegram."""
import re
from datetime import datetime

import app
from owner_profile import is_owner
from telegram_api import send_message

_LOAD = re.compile(r"^\d+(?:[.,]\d+)?\s*(?:kg|lb|lbs)?$", re.I)
_REPS = re.compile(r"^\d{1,3}\s*(?:reps?|repetições?)?$", re.I)


def parse_quick_series(text):
    parts = [part.strip() for part in (text or "").split("|")]
    if len(parts) != 3 or not all(parts):
        return None
    exercise, load, reps = parts
    if len(exercise) > 110 or not _LOAD.fullmatch(load) or not _REPS.fullmatch(reps):
        return None
    return exercise, load, reps


def _date_of_message(message):
    # O Telegram informa quando a mensagem foi criada, não quando o webhook a recebeu.
    # Assim uma série enviada pouco antes da meia-noite não migra de dia após reconectar.
    timestamp = message.get("date")
    if timestamp is not None:
        try:
            return datetime.fromtimestamp(int(timestamp), tz=app.LOCAL_TZ).date()
        except (ValueError, OverflowError, TypeError):
            pass
    return app.now_local().date()


async def _find(db, table, uid, message_id):
    return await db.prepare(
        f"SELECT set_number FROM {table} WHERE user_id=? AND source_message_id=? LIMIT 1"
    ).bind(uid, message_id).first()


async def handle_message(db, token, message):
    parsed = parse_quick_series(message.get("text"))
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None or parsed is None:
        return False

    chat_id = int(chat_id)
    user = await db.prepare(
        "SELECT id FROM users WHERE telegram_chat_id=?"
    ).bind(chat_id).first()
    if user is None:
        return False
    uid = int(app.rowget(user, "id"))
    owner = is_owner(chat_id)
    table = "protocol_mass_set_logs" if owner else "workout_set_logs"
    message_id = message.get("message_id")
    if message_id is None:
        await send_message(token, chat_id, "⚠️ Não recebi o identificador da mensagem; não registrei a série.")
        return True

    message_id = int(message_id)
    existing = await _find(db, table, uid, message_id)
    if existing:
        await send_message(token, chat_id, "↩️ Essa série já estava registrada. Nenhuma duplicação.")
        return True

    exercise, load, reps = parsed
    target_date = _date_of_message(message)
    wd, week, active, exercises = await app.workout_plan(db, uid, owner, target_date)
    if owner and not active:
        await send_message(token, chat_id, "⚠️ Seu protocolo não está ativo. Abra Treino para iniciar ou reiniciar; série não salva.")
        return True

    target = next((e for e in exercises if app.norm(e.get("name")) == app.norm(exercise)), None)
    if not target:
        await send_message(
            token, chat_id,
            f"⚠️ “{exercise}” não corresponde à ficha de {wd}. Nada foi salvo. Confira o nome em Treino de hoje."
        )
        return True

    exercise = target["name"]
    weekday = app.WEEKDAY_NAMES[target_date.weekday()]
    for _ in range(3):
        # Cada update do Telegram é a chave de idempotência. INSERT OR IGNORE
        # evita perda por retry, e a leitura final comprova a escrita.
        if owner:
            stmt = db.prepare(
                "INSERT OR IGNORE INTO protocol_mass_set_logs"
                "(user_id,week,weekday,exercise_name,set_number,load,reps,source_message_id) "
                "SELECT ?,?,?,?,COALESCE(MAX(set_number),0)+1,?,?,? "
                "FROM protocol_mass_set_logs "
                "WHERE user_id=? AND week=? AND weekday=? AND exercise_name=?"
            ).bind(uid, week or 1, weekday, exercise, load, reps, message_id,
                   uid, week or 1, weekday, exercise)
        else:
            stmt = db.prepare(
                "INSERT OR IGNORE INTO workout_set_logs"
                "(user_id,workout_date,exercise_name,set_number,load,reps,source_message_id) "
                "SELECT ?,?,?,COALESCE(MAX(set_number),0)+1,?,?,? "
                "FROM workout_set_logs WHERE user_id=? AND workout_date=? AND exercise_name=?"
            ).bind(uid, target_date.isoformat(), exercise, load, reps, message_id,
                   uid, target_date.isoformat(), exercise)
        await stmt.run()
        inserted = await _find(db, table, uid, message_id)
        if inserted:
            number = int(app.rowget(inserted, "set_number"))
            await send_message(
                token, chat_id,
                f"✅ {exercise} • série {number}\n{load} × {reps}\nRegistrada em {target_date.strftime('%d/%m')}."
            )
            return True

    await send_message(token, chat_id, "⚠️ Não consegui confirmar essa série no banco. Confira o histórico antes de reenviar.")
    return True
