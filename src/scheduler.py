import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes

from src.assistant_state import is_day_off, list_routines
from src.config import BUTLER_TIMEZONE, DATABASE_PATH
from src.daily_store import clear_snooze, list_items
from src.database import preferred_name
from src.personality import choose, everyday_tone

WEEKDAY_NAMES = {0:"segunda-feira",1:"terça-feira",2:"quarta-feira",3:"quinta-feira",4:"sexta-feira",5:"sábado",6:"domingo"}
WEEKDAY_SHORT = {0:"seg",1:"ter",2:"qua",3:"qui",4:"sex",5:"sab",6:"dom"}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(Path(DATABASE_PATH)); conn.row_factory = sqlite3.Row; return conn


def _chat_ids() -> list[int]:
    with _connect() as conn:
        return [int(r[0]) for r in conn.execute("SELECT telegram_chat_id FROM users").fetchall()]


def _active_classes(weekday: str, start_time: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            """SELECT s.name, cs.start_time, cs.end_time, cs.location FROM class_sessions cs
            JOIN subjects s ON s.id = cs.subject_id WHERE s.active = 1 AND cs.weekday = ? AND cs.start_time = ? ORDER BY s.name""",
            (weekday, start_time)).fetchall()


def _routine_matches(days: str | None, weekday_short: str, weekday_full: str) -> bool:
    if not days or days.strip().lower() in {"todos", "todo dia", "diario", "diário"}: return True
    normalized = days.lower().replace(";", ",")
    values = {x.strip() for x in normalized.split(",")}
    return weekday_short in values or weekday_full in values


def _address(text: str, chat_id: int) -> str:
    return text.replace("chefe", preferred_name(chat_id))


async def proactive_tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_day_off():
        return
    tz = ZoneInfo(BUTLER_TIMEZONE)
    now = datetime.now(tz).replace(second=0, microsecond=0)
    sent: set[str] = context.application.bot_data.setdefault("sent_reminders", set())
    chats = _chat_ids()
    if not chats: return

    target = now + timedelta(minutes=10)
    for row in _active_classes(WEEKDAY_NAMES[target.weekday()], target.strftime("%H:%M")):
        key = f"class:{target.date()}:{row['name']}:{row['start_time']}"
        if key in sent: continue
        opener = choose("class_reminder", everyday_tone())
        text = (f"🎓 *Aula em 10 minutos*\n\n{opener}\n\n*{row['name']}*\n🕐 {row['start_time']}–{row['end_time']}\n"
                f"📍 {row['location'] or 'local não informado'}")
        for chat in chats:
            await context.bot.send_message(chat_id=chat, text=_address(text, chat), parse_mode="Markdown")
        sent.add(key)

    for item in list_items(only_pending=True):
        should_send = False
        reason = "normal"
        if item["snoozed_until"]:
            try:
                snooze_at = datetime.fromisoformat(item["snoozed_until"]).replace(tzinfo=tz)
                if snooze_at == now:
                    should_send = True; reason = "snooze"; clear_snooze(item["id"])
            except ValueError: pass
        if not should_send and item["due_date"] and item["due_time"]:
            try: due = datetime.fromisoformat(f"{item['due_date']}T{item['due_time']}").replace(tzinfo=tz)
            except ValueError: continue
            should_send = due - timedelta(minutes=int(item["reminder_minutes"] or 0)) == now
        if not should_send: continue
        key = f"item:{item['id']}:{now.isoformat()}:{reason}"
        if key in sent: continue
        icons = {"tarefa":"✅","compromisso":"📅","pendencia":"📌"}
        labels = {"tarefa":"Tarefa","compromisso":"Compromisso","pendencia":"Pendência"}
        opener = choose("task_reminder", everyday_tone())
        text = f"{icons.get(item['kind'],'🔔')} *{labels.get(item['kind'],'Lembrete')}*\n\n{opener}\n\n*{item['title']}*"
        if item["due_time"]: text += f"\n🕐 {item['due_time']}"
        if item["details"]: text += f"\n📝 {item['details']}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Concluir", callback_data=f"daily_done:{item['id']}")],
            [InlineKeyboardButton("⏰ +10 min", callback_data=f"daily_snooze:{item['id']}:10"), InlineKeyboardButton("⏰ +30 min", callback_data=f"daily_snooze:{item['id']}:30")]
        ])
        for chat in chats:
            await context.bot.send_message(chat_id=chat, text=_address(text, chat), parse_mode="Markdown", reply_markup=keyboard)
        sent.add(key)

    for routine in list_routines():
        if not routine["time_hhmm"]: continue
        if not _routine_matches(routine["weekdays"], WEEKDAY_SHORT[now.weekday()], WEEKDAY_NAMES[now.weekday()]): continue
        try:
            due = datetime.fromisoformat(f"{now.date().isoformat()}T{routine['time_hhmm']}").replace(tzinfo=tz)
        except ValueError: continue
        reminder_at = due - timedelta(minutes=int(routine["reminder_minutes"] or 0))
        if reminder_at != now: continue
        key = f"routine:{routine['id']}:{now.date()}"
        if key in sent: continue
        opener = choose("routine_reminder", everyday_tone())
        text = f"🧘 *Um cuidado rápido*\n\n{opener}\n\n*{routine['name']}*\nCategoria: {routine['category']}"
        for chat in chats:
            await context.bot.send_message(chat_id=chat, text=_address(text, chat), parse_mode="Markdown")
        sent.add(key)

    if len(sent) > 2000:
        context.application.bot_data["sent_reminders"] = set(list(sent)[-500:])


def register_scheduler(application: Application) -> None:
    if application.job_queue is None:
        raise RuntimeError("JobQueue indisponível. Instale python-telegram-bot[job-queue].")
    application.job_queue.run_repeating(proactive_tick, interval=30, first=5, name="butler-proactive-tick")
