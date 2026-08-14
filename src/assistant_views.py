from collections import defaultdict
from datetime import date, datetime

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

from src.daily_store import list_items
from src.database import list_subjects
from src.home_handlers import HOME_KEYBOARD
from src.home_store import list_missing_groceries, list_workout
from src.home_menu import MAIN_KEYBOARD

WEEKDAYS = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

ITEM_ICONS = {"tarefa": "✅", "compromisso": "📅", "pendencia": "📌"}


async def whats_missing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_missing_groceries()
    if not rows:
        await update.message.reply_text("🛒 No momento não há nada marcado como faltando em casa.", reply_markup=HOME_KEYBOARD)
        raise ApplicationHandlerStop
    parts = ["🛒 *Está faltando:*\n"]
    for row in rows:
        qty = f" — {row['quantity']}" if row["quantity"] else ""
        note = f" ({row['note']})" if row["note"] else ""
        parts.append(f"• {row['name']}{qty}{note}")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=HOME_KEYBOARD)
    raise ApplicationHandlerStop


async def today_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = date.today()
    weekday = WEEKDAYS[today.weekday()]
    timeline: list[tuple[str, str]] = []

    for row in list_subjects(include_locked=False):
        if row["weekday"] == weekday:
            location = row["location"] or "Local não informado"
            timeline.append((row["start_time"], f"🎓 *{row['name']}* — {row['start_time']}–{row['end_time']}\n   📍 {location}"))

    for row in list_items(only_pending=True):
        if row["due_date"] != today.isoformat():
            continue
        icon = ITEM_ICONS.get(row["kind"], "•")
        when = row["due_time"] or "99:99"
        time_label = f"{row['due_time']} — " if row["due_time"] else ""
        timeline.append((when, f"{icon} {time_label}*{row['title']}*"))

    workout_rows = [row for row in list_workout() if row["weekday"] == weekday]
    workout_focus = None
    exercises = []
    for row in workout_rows:
        workout_focus = row["focus"]
        if row["name"]:
            exercises.append(row)

    parts = [f"🗓️ *Hoje — {weekday.capitalize()}, {today.strftime('%d/%m/%Y')}*\n"]
    if timeline:
        for _, text in sorted(timeline, key=lambda item: item[0]):
            parts.append(text)
    else:
        parts.append("Nenhuma aula, tarefa, compromisso ou pendência marcada para hoje.")

    if workout_focus:
        parts.append(f"\n🏋️ *Musculação — {workout_focus}*")
        for row in exercises:
            load = f" — {row['load']}" if row["load"] else ""
            scheme = f"{row['sets']}x{row['reps']}" if row["sets"] else (row["reps"] or "")
            parts.append(f"• {row['name']} — {scheme}{load}")

    missing_count = len(list_missing_groceries())
    if missing_count:
        parts.append(f"\n🛒 Há *{missing_count}* item(ns) marcado(s) como faltando em casa.")

    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    raise ApplicationHandlerStop


def register_assistant_views(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(r"(?i)^o que (?:está|esta) faltando\??$"), whats_missing), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^🗓️ Hoje$"), today_overview), group=-2)
