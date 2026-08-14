from datetime import date, datetime, timedelta

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, ConversationHandler, MessageHandler, filters

from src.daily_store import list_items
from src.database import list_subjects
from src.home_store import list_missing_groceries, list_workout
from src.ui_layout import COTIDIANO_KEYBOARD, MAIN_KEYBOARD

WEEKDAYS = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

ITEM_ICONS = {"tarefa": "✅", "compromisso": "📅"}
AGENDA_DATE = 720
AGENDA_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["⏭️ Amanhã", "📆 Outra data"],
        ["🗓️ Próximos 7 dias", "📚 Histórico"],
        ["🏠 Menu principal"],
    ],
    resize_keyboard=True,
)
CANCEL_DATE_KEYBOARD = ReplyKeyboardMarkup([["❌ Cancelar ação"]], resize_keyboard=True)


def _day_parts(target: date, include_overdue: bool = False) -> list[str]:
    weekday = WEEKDAYS[target.weekday()]
    timeline: list[tuple[str, str]] = []
    overdue_tasks = []

    for row in list_subjects(include_locked=False):
        if row["weekday"] == weekday:
            location = row["location"] or "Local não informado"
            timeline.append((row["start_time"], f"🎓 *{row['name']}* — {row['start_time']}–{row['end_time']}\n   📍 {location}"))

    for row in list_items(only_pending=True):
        if include_overdue and row["kind"] == "tarefa" and row["due_date"] and row["due_date"] < target.isoformat():
            overdue_tasks.append(row)
            continue
        if row["due_date"] != target.isoformat():
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

    parts = []
    if timeline:
        for _, text in sorted(timeline, key=lambda item: item[0]):
            parts.append(text)
    else:
        parts.append("Nada marcado. Um raro espaço em branco no calendário.")

    if overdue_tasks:
        parts.append("\n📌 *Pendências — tarefas vencidas*")
        for row in overdue_tasks:
            due = datetime.fromisoformat(row["due_date"]).strftime("%d/%m")
            parts.append(f"• *{row['title']}* — venceu em {due}")

    if workout_focus:
        parts.append(f"\n🏋️ *Musculação — {workout_focus}*")
        for row in exercises:
            load = f" — {row['load']}" if row["load"] else ""
            scheme = f"{row['sets']}x{row['reps']}" if row["sets"] else (row["reps"] or "")
            parts.append(f"• {row['name']} — {scheme}{load}")

    return parts


async def whats_missing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_missing_groceries()
    if not rows:
        await update.message.reply_text("🛒 No momento não há nada marcado como faltando em casa.", reply_markup=COTIDIANO_KEYBOARD)
        raise ApplicationHandlerStop
    parts = ["🛒 *Está faltando:*\n"]
    for row in rows:
        qty = f" — {row['quantity']}" if row["quantity"] else ""
        note = f" ({row['note']})" if row["note"] else ""
        parts.append(f"• {row['name']}{qty}{note}")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=COTIDIANO_KEYBOARD)
    raise ApplicationHandlerStop


async def today_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = date.today()
    weekday = WEEKDAYS[today.weekday()]
    parts = [f"🗓️ *Hoje — {weekday.capitalize()}, {today.strftime('%d/%m/%Y')}*\n"]
    parts.extend(_day_parts(today, include_overdue=True))

    missing_count = len(list_missing_groceries())
    if missing_count:
        parts.append(f"\n🛒 Há *{missing_count}* item(ns) faltando em casa.")

    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=AGENDA_KEYBOARD)
    raise ApplicationHandlerStop


async def tomorrow_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target = date.today() + timedelta(days=1)
    weekday = WEEKDAYS[target.weekday()]
    parts = [f"⏭️ *Amanhã — {weekday.capitalize()}, {target.strftime('%d/%m/%Y')}*\n"]
    parts.extend(_day_parts(target))
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=AGENDA_KEYBOARD)
    raise ApplicationHandlerStop


async def next_days_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    parts = ["🗓️ *Próximos 7 dias*\n"]
    start = date.today() + timedelta(days=1)
    for offset in range(7):
        target = start + timedelta(days=offset)
        weekday = WEEKDAYS[target.weekday()]
        parts.append(f"\n*{weekday.capitalize()}, {target.strftime('%d/%m')}*")
        day_parts = _day_parts(target)
        if len(day_parts) == 1 and day_parts[0].startswith("Nada marcado"):
            parts.append("• Nada marcado.")
        else:
            parts.extend(day_parts)
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=AGENDA_KEYBOARD)
    raise ApplicationHandlerStop


async def another_date_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📆 Qual data você quer consultar?\n\nDigite `DD/MM` ou `DD/MM/AAAA`. Ex.: `18/08`.",
        parse_mode="Markdown",
        reply_markup=CANCEL_DATE_KEYBOARD,
    )
    return AGENDA_DATE


async def another_date_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        await update.message.reply_text("Consulta cancelada.", reply_markup=AGENDA_KEYBOARD)
        return ConversationHandler.END

    target = None
    for fmt in ("%d/%m/%Y", "%d/%m"):
        try:
            parsed = datetime.strptime(text, fmt)
            year = parsed.year if fmt == "%d/%m/%Y" else date.today().year
            target = date(year, parsed.month, parsed.day)
            if fmt == "%d/%m" and target < date.today():
                target = date(year + 1, parsed.month, parsed.day)
            break
        except ValueError:
            continue

    if target is None:
        await update.message.reply_text("Não reconheci essa data. Use `DD/MM` ou `DD/MM/AAAA`.", parse_mode="Markdown")
        return AGENDA_DATE

    weekday = WEEKDAYS[target.weekday()]
    parts = [f"📆 *{weekday.capitalize()}, {target.strftime('%d/%m/%Y')}*\n"]
    parts.extend(_day_parts(target))
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=AGENDA_KEYBOARD)
    return ConversationHandler.END


def register_assistant_views(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(r"(?i)^o que (?:está|esta) faltando\??$"), whats_missing), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^🗓️ Hoje$"), today_overview), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^⏭️ Amanhã$"), tomorrow_overview), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^🗓️ Próximos 7 dias$"), next_days_overview), group=-2)
    application.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(r"^📆 Outra data$"), another_date_start)],
            states={AGENDA_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, another_date_receive)]},
            fallbacks=[],
        ),
        group=-3,
    )
