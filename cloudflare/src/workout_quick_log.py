"""Registro rápido de séries para conexão instável.

O Telegram continua sendo responsável por entregar a mensagem ao Worker. Este
módulo torna cada registro autossuficiente para que mensagens enfileiradas pelo
cliente possam ser processadas independentemente quando a conexão voltar.
"""
import re

import app
from telegram_api import send_message


def parse_quick_series(text):
    parts=[p.strip() for p in (text or "").split("|")]
    if len(parts)!=3 or not all(parts):
        return None
    exercise,load,reps=parts
    if not re.search(r"\d",load) or not re.search(r"\d",reps):
        return None
    return exercise,load,reps


async def _user(db,chat_id):
    return await db.prepare(
        "SELECT id,is_owner FROM users WHERE telegram_chat_id=?"
    ).bind(int(chat_id)).first()


async def _already_received(db,uid,owner,message_id):
    if message_id is None:
        return False
    table="protocol_mass_set_logs" if owner else "workout_set_logs"
    row=await db.prepare(
        f"SELECT id FROM {table} WHERE user_id=? AND source_message_id=? LIMIT 1"
    ).bind(uid,int(message_id)).first()
    return bool(row)


async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    parsed=parse_quick_series(message.get("text"))
    if chat_id is None or not parsed:
        return False

    row=await _user(db,chat_id)
    if not row:
        return False
    uid=int(app.rowget(row,"id"))
    owner=bool(int(app.rowget(row,"is_owner",0) or 0))
    message_id=message.get("message_id")

    if await _already_received(db,uid,owner,message_id):
        await send_message(token,int(chat_id),"↩️ Essa série já tinha sido registrada. Não dupliquei.")
        return True

    exercise,load,reps=parsed
    wd,week,active,exercises=await app.workout_plan(db,uid,owner)
    target=next((e for e in exercises if app.norm(e.get("name"))==app.norm(exercise)),None)
    if not target:
        await send_message(
            token,int(chat_id),
            f"⚠️ Não achei “{exercise}” no treino de hoje. Use o nome exibido na ficha para evitar registrar no exercício errado.",
            reply_markup=app.kb(app.WORKOUT_KB),
        )
        return True

    exercise=target["name"]
    today=app.now_local().date()
    if owner:
        weekday=app.WEEKDAY_NAMES[today.weekday()]
        count=await db.prepare(
            "SELECT COUNT(*) n FROM protocol_mass_set_logs WHERE user_id=? AND week=? AND weekday=? AND exercise_name=?"
        ).bind(uid,week or 1,weekday,exercise).first()
        sn=int(app.rowget(count,"n",0))+1
        await db.prepare(
            "INSERT OR IGNORE INTO protocol_mass_set_logs(user_id,week,weekday,exercise_name,set_number,load,reps,source_message_id) VALUES(?,?,?,?,?,?,?,?)"
        ).bind(uid,week or 1,weekday,exercise,sn,load,reps,message_id).run()
    else:
        count=await db.prepare(
            "SELECT COUNT(*) n FROM workout_set_logs WHERE user_id=? AND workout_date=? AND exercise_name=?"
        ).bind(uid,today.isoformat(),exercise).first()
        sn=int(app.rowget(count,"n",0))+1
        await db.prepare(
            "INSERT OR IGNORE INTO workout_set_logs(user_id,workout_date,exercise_name,set_number,load,reps,source_message_id) VALUES(?,?,?,?,?,?,?)"
        ).bind(uid,today.isoformat(),exercise,sn,load,reps,message_id).run()

    await send_message(
        token,int(chat_id),
        f"✅ {exercise} — série {sn}: {load} × {reps}.",
        reply_markup=app.kb(app.WORKOUT_KB),
    )
    return True
