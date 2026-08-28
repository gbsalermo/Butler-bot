"""Integra clima às consultas de agenda e permite configurar a cidade por texto."""

import re
import unicodedata
from datetime import datetime, timedelta, timezone

import app
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message
from weather_service import forecast_text, get_location, set_city, set_morning_enabled

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
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


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


def _today():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ).date()


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _send_agenda_with_weather(db, token, chat_id, uid, target, label):
    agenda = await app.agenda_text(db, uid, target, True)
    weather = await forecast_text(db, uid, target, heading=f"Tempo {label}")
    if weather:
        agenda += "\n\n" + weather
    else:
        agenda += (
            "\n\n🌤️ Clima ainda não configurado. "
            "Diga, por exemplo, `clima em Salvador` para eu saber qual cidade usar."
        )
    await send_message(token, chat_id, agenda, reply_markup=_kb(app.AGENDA_KB))


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    n = _norm(text)
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    chat_id = int(chat_id)
    uid = await _uid(db, chat_id)
    if uid is None:
        return False

    city_match = re.match(r"^(?:butler\s+)?(?:clima|tempo|previsao)(?: do tempo)?\s+em\s+(.+)$", n)
    if city_match:
        raw_city = re.sub(
            r"^(?:Butler[,!:\-]?\s*)?(?:clima|tempo|previs[aã]o)(?: do tempo)?\s+em\s+",
            "",
            text,
            flags=re.I,
        ).strip()
        try:
            location = await set_city(db, uid, raw_city)
            today = _today()
            weather = await forecast_text(db, uid, today, heading="Tempo hoje")
            await send_message(
                token,
                chat_id,
                f"📍 Clima configurado para {location['city']}."
                + (f"\n\n{weather}" if weather else ""),
                reply_markup=_kb(app.MAIN_KB),
            )
        except Exception:
            await send_message(
                token,
                chat_id,
                "Não encontrei essa cidade com segurança. Tente `clima em Cruz das Almas, BA` ou informe cidade e estado.",
                reply_markup=_kb(app.MAIN_KB),
            )
        return True

    if n in ("qual cidade do clima", "qual cidade do tempo", "cidade do clima", "onde esta o clima"):
        location = await get_location(db, uid)
        if location:
            await send_message(token, chat_id, f"📍 Estou usando {location['city']} para o clima.", reply_markup=_kb(app.MAIN_KB))
        else:
            await send_message(token, chat_id, "Ainda não tenho uma cidade para o clima. Diga `clima em Salvador`.", reply_markup=_kb(app.MAIN_KB))
        return True

    if n in ("desativar clima de manha", "desativar boletim do clima", "sem clima de manha"):
        ok = await set_morning_enabled(db, uid, False)
        await send_message(
            token,
            chat_id,
            "🔕 Clima removido do resumo da manhã." if ok else "Configure uma cidade primeiro com `clima em <cidade>`.",
            reply_markup=_kb(app.MAIN_KB),
        )
        return True

    if n in ("ativar clima de manha", "ativar boletim do clima", "clima de manha"):
        ok = await set_morning_enabled(db, uid, True)
        await send_message(
            token,
            chat_id,
            "🔔 Clima ativado no resumo da manhã." if ok else "Configure uma cidade primeiro com `clima em <cidade>`.",
            reply_markup=_kb(app.MAIN_KB),
        )
        return True

    today = _today()
    tomorrow = today + timedelta(days=1)

    today_agenda = text == "🗓️ Hoje" or n in {
        "o que tenho hoje",
        "o que eu tenho hoje",
        "minha agenda hoje",
        "agenda de hoje",
        "tarefas de hoje",
    }
    tomorrow_agenda = text == "⏭️ Amanhã" or n in {
        "o que tenho amanha",
        "o que eu tenho amanha",
        "minha agenda amanha",
        "agenda de amanha",
        "tarefas de amanha",
        "o que tenho para amanha",
        "o que eu tenho para amanha",
    }

    if today_agenda:
        try:
            await _send_agenda_with_weather(db, token, chat_id, uid, today, "hoje")
        except Exception as exc:
            print(f"[weather] agenda-today-error type={type(exc).__name__} message={str(exc)[:220]}")
            await send_message(token, chat_id, await app.agenda_text(db, uid, today, True), reply_markup=_kb(app.AGENDA_KB))
        return True

    if tomorrow_agenda:
        try:
            await _send_agenda_with_weather(db, token, chat_id, uid, tomorrow, "amanhã")
        except Exception as exc:
            print(f"[weather] agenda-tomorrow-error type={type(exc).__name__} message={str(exc)[:220]}")
            await send_message(token, chat_id, await app.agenda_text(db, uid, tomorrow, True), reply_markup=_kb(app.AGENDA_KB))
        return True

    weather_today = n in {
        "clima hoje",
        "tempo hoje",
        "previsao hoje",
        "previsao do tempo hoje",
        "como esta o tempo hoje",
        "como vai estar o tempo hoje",
    }
    weather_tomorrow = n in {
        "clima amanha",
        "tempo amanha",
        "previsao amanha",
        "previsao do tempo amanha",
        "como vai estar o tempo amanha",
    }
    if weather_today or weather_tomorrow:
        target = tomorrow if weather_tomorrow else today
        heading = "Tempo amanhã" if weather_tomorrow else "Tempo hoje"
        try:
            weather = await forecast_text(db, uid, target, heading=heading)
        except Exception as exc:
            print(f"[weather] direct-query-error type={type(exc).__name__} message={str(exc)[:220]}")
            weather = None
        if weather:
            await send_message(token, chat_id, weather, reply_markup=_kb(app.MAIN_KB))
        else:
            await send_message(
                token,
                chat_id,
                "🌤️ Ainda não tenho uma cidade configurada. Diga `clima em Salvador`.",
                reply_markup=_kb(app.MAIN_KB),
            )
        return True

    return False
