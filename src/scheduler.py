import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes

from src.assistant_state import is_day_off, list_routines
from src.config import BUTLER_TIMEZONE
from src.daily_store import clear_snooze, list_items
from src.database import preferred_name
from src.morning_context import morning_summary_with_yesterday
from src.personality import choose, everyday_tone
from src.summary_engine import weekly_summary
from src.user_scope import (
    initialize_current_user_storage,
    multiuser_enabled,
    registered_chat_ids,
    resolve_database_path,
    set_current_chat_id,
)

WEEKDAY_NAMES = {0:"segunda-feira",1:"terça-feira",2:"quarta-feira",3:"quinta-feira",4:"sexta-feira",5:"sábado",6:"domingo"}
WEEKDAY_SHORT = {0:"seg",1:"ter",2:"qua",3:"qui",4:"sex",5:"sab",6:"dom"}

MORNING_SUMMARY_TIME = os.getenv("BUTLER_MORNING_SUMMARY_TIME", "07:30")
WEEKLY_SUMMARY_TIME = os.getenv("BUTLER_WEEKLY_SUMMARY_TIME", "20:00")
WEEKLY_SUMMARY_WEEKDAY = int(os.getenv("BUTLER_WEEKLY_SUMMARY_WEEKDAY", "6"))  # 0=seg ... 6=dom


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(resolve_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def _chat_ids() -> list[int]:
    if multiuser_enabled():
        return registered_chat_ids()
    with _connect() as conn:
        try:
            return [int(r[0]) for r in conn.execute("SELECT telegram_chat_id FROM users").fetchall()]
        except sqlite3.OperationalError:
            return []


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


async def _automatic_summaries(context: ContextTypes.DEFAULT_TYPE, chat_id: int, now: datetime, sent: set[str]) -> None:
    current = now.strftime("%H:%M")
    name = preferred_name(chat_id)

    if current == MORNING_SUMMARY_TIME:
        key = f"{chat_id}:summary:morning:{now.date()}"
        if key not in sent:
            await context.bot.send_message(
                chat_id=chat_id,
                text=morning_summary_with_yesterday(name, now.date()),
                parse_mode="Markdown",
            )
            sent.add(key)

    if now.weekday() == WEEKLY_SUMMARY_WEEKDAY and current == WEEKLY_SUMMARY_TIME:
        key = f"{chat_id}:summary:weekly:{now.date()}"
        if key not in sent:
            await context.bot.send_message(
                chat_id=chat_id,
                text=weekly_summary(name, now.date()),
                parse_mode="Markdown",
            )
            sent.add(key)


async def _tick_for_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int, now: datetime, sent: set[str]) -> None:
    set_current_chat_id(chat_id)
    if multiuser_enabled():
        initialize_current_user_storage()

    if is_day_off():
        return

    await _automatic_summaries(context, chat_id, now, sent)

    tz = ZoneInfo(BUTLER_TIMEZONE)
    target = now + timedelta(minutes=10)

    for row in _active_classes(WEEKDAY_NAMES[target.weekday()], target.strftime("%H:%M")):
        key = f"{chat_id}:class:{target.date()}:{row['name']}:{row['start_time']}"
        if key in sent:
            continue
        opener = choose("class_reminder", everyday_tone())
        text = (
            f"🎓 *Aula em 10 minutos*\n\n{opener}\n\n*{row['name']}*\n"
            f"🕐 {row['start_time']}–{row['end_time']}\n📍 {row['location'] or 'local não informado'}"
        )
        await context.bot.send_message(chat_id=chat_id, text=_address(text, chat_id), parse_mode="Markdown")
        sent.add(key)

    for item in list_items(only_pending=True):
        should_send = False
        reason = "normal"
        if item["snoozed_until"]:
            try:
                snooze_at = datetime.fromisoformat(item["snoozed_until"]).replace(tzinfo=tz)
                if snooze_at == now:
                    should_send = True
                    reason = "snooze"
                    clear_snooze(item["id"])
            except ValueError:
                pass
        if not should_send and item["due_date"] and item["due_time"]:
            try:
                due = datetime.fromisoformat(f"{item['due_date']}T{item['due_time']}").replace(tzinfo=tz)
            except ValueError:
                continue
            should_send = due - timedelta(minutes=int(item["reminder_minutes"] or 0)) == now
        if not should_send:
            continue

        key = f"{chat_id}:item:{item['id']}:{now.isoformat()}:{reason}"
        if key in sent:
            continue
        icons = {"tarefa":"✅", "compromisso":"📅"}
        labels = {"tarefa":"Tarefa", "compromisso":"Compromisso"}
        opener = choose("task_reminder", everyday_tone())
        text = f"{icons.get(item['kind'],'🔔')} *{labels.get(item['kind'],'Lembrete')}*\n\n{opener}\n\n*{item['title']}*"
        if item["due_time"]:
            text += f"\n🕐 {item['due_time']}"
        if item["details"]:
            text += f"\n📝 {item['details']}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Concluir", callback_data=f"daily_done:{item['id']}")],
            [InlineKeyboardButton("⏰ +10 min", callback_data=f"daily_snooze:{item['id']}:10"), InlineKeyboardButton("⏰ +30 min", callback_data=f"daily_snooze:{item['id']}:30")]
        ])
        await context.bot.send_message(
            chat_id=chat_id,
            text=_address(text, chat_id),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        sent.add(key)

    for routine in list_routines():
        if not routine["time_hhmm"]:
            continue
        if not _routine_matches(routine["weekdays"], WEEKDAY_SHORT[now.weekday()], WEEKDAY_NAMES[now.weekday()]):
            continue
        try:
            due = datetime.fromisoformat(f"{now.date().isoformat()}T{routine['time_hhmm']}").replace(tzinfo=tz)
        except ValueError:
            continue
        reminder_at = due - timedelta(minutes=int(routine["reminder_minutes"] or 0))
        if reminder_at != now:
            continue
        key = f"{chat_id}:routine:{routine['id']}:{now.date()}"
        if key in sent:
            continue
        opener = choose("routine_reminder", everyday_tone())
        text = f"🧘 *Um cuidado rápido*\n\n{opener}\n\n*{routine['name']}*\nCategoria: {routine['category']}"
        await context.bot.send_message(chat_id=chat_id, text=_address(text, chat_id), parse_mode="Markdown")
        sent.add(key)


async def proactive_tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    tz = ZoneInfo(BUTLER_TIMEZONE)
    now = datetime.now(tz).replace(second=0, microsecond=0)
    sent: set[str] = context.application.bot_data.setdefault("sent_reminders", set())

    for chat_id in _chat_ids():
        await _tick_for_chat(context, chat_id, now, sent)

    set_current_chat_id(None)
    if len(sent) > 3000:
        context.application.bot_data["sent_reminders"] = set(list(sent)[-800:])


def register_scheduler(application: Application) -> None:
    if application.job_queue is None:
        raise RuntimeError("JobQueue indisponível. Instale python-telegram-bot[job-queue].")
    application.job_queue.run_repeating(proactive_tick, interval=30, first=5, name="butler-proactive-tick")
