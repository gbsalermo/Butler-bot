import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram.ext import Application, ContextTypes

from src.config import BUTLER_TIMEZONE, DATABASE_PATH
from src.daily_store import list_items

WEEKDAY_NAMES = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(Path(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _chat_ids() -> list[int]:
    with _connect() as conn:
        return [int(row[0]) for row in conn.execute("SELECT telegram_chat_id FROM users").fetchall()]


def _active_classes(weekday: str, start_time: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            """
            SELECT s.name, cs.start_time, cs.end_time, cs.location
            FROM class_sessions cs
            JOIN subjects s ON s.id = cs.subject_id
            WHERE s.active = 1
              AND cs.weekday = ?
              AND cs.start_time = ?
            ORDER BY s.name
            """,
            (weekday, start_time),
        ).fetchall()


async def proactive_tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    tz = ZoneInfo(BUTLER_TIMEZONE)
    now = datetime.now(tz).replace(second=0, microsecond=0)
    sent: set[str] = context.application.bot_data.setdefault("sent_reminders", set())
    chats = _chat_ids()
    if not chats:
        return

    # Aulas: aviso padrão 10 minutos antes.
    target = now + timedelta(minutes=10)
    weekday = WEEKDAY_NAMES[target.weekday()]
    classes = _active_classes(weekday, target.strftime("%H:%M"))
    for class_row in classes:
        key = f"class:{target.date()}:{class_row['name']}:{class_row['start_time']}"
        if key in sent:
            continue
        location = class_row["location"] or "local não informado"
        text = (
            "🎓 *Aula em 10 minutos*\n\n"
            f"*{class_row['name']}*\n"
            f"🕐 {class_row['start_time']}–{class_row['end_time']}\n"
            f"📍 {location}\n\n"
            "Hora de se organizar para a aula."
        )
        for chat_id in chats:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        sent.add(key)

    # Tarefas, compromissos e pendências com data/hora.
    for item in list_items(only_pending=True):
        if not item["due_date"] or not item["due_time"]:
            continue
        try:
            due = datetime.fromisoformat(f"{item['due_date']}T{item['due_time']}").replace(tzinfo=tz)
        except ValueError:
            continue
        reminder_at = due - timedelta(minutes=int(item["reminder_minutes"] or 10))
        if reminder_at != now:
            continue
        key = f"item:{item['id']}:{due.isoformat()}"
        if key in sent:
            continue
        icons = {"tarefa": "✅", "compromisso": "📅", "pendencia": "📌"}
        labels = {"tarefa": "Tarefa", "compromisso": "Compromisso", "pendencia": "Pendência"}
        kind = item["kind"]
        text = (
            f"{icons.get(kind, '🔔')} *{labels.get(kind, 'Lembrete')} chegando*\n\n"
            f"*{item['title']}*\n"
            f"🕐 {item['due_time']}"
        )
        if item["details"]:
            text += f"\n📝 {item['details']}"
        for chat_id in chats:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        sent.add(key)

    # Evita crescimento infinito do conjunto em processos longos.
    if len(sent) > 2000:
        context.application.bot_data["sent_reminders"] = set(list(sent)[-500:])


def register_scheduler(application: Application) -> None:
    if application.job_queue is None:
        raise RuntimeError("JobQueue indisponível. Instale python-telegram-bot[job-queue].")
    application.job_queue.run_repeating(proactive_tick, interval=30, first=5, name="butler-proactive-tick")
