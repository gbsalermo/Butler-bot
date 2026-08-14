import re
from collections import defaultdict
from datetime import date

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from src.protocol_mass_data import WEEKS
from src.protocol_mass_store import (
    exercise_history,
    exercise_logs,
    get_state,
    log_exercise,
    log_set,
    logged_exercise_names,
    set_logs,
)
from src.protocol_mass_ui import ACTIVE_PROTOCOL_KEYBOARD

SERIES_EXERCISE, SERIES_COUNT, SERIES_LOAD, SERIES_REPS = range(600, 604)
HISTORY_EXERCISE = 610

CANCEL_KEYBOARD = ReplyKeyboardMarkup([["❌ Cancelar ação"]], resize_keyboard=True)

WEEKDAY = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}


def _today_name() -> str:
    return WEEKDAY[date.today().weekday()]


def _today_exercises(week: int) -> list[dict]:
    return WEEKS.get(str(week), {}).get(_today_name(), [])


def _listing(exercises: list[dict]) -> str:
    return "\n".join(f"{i}. {exercise['name']} — {exercise['series']}" for i, exercise in enumerate(exercises, 1))


def _simple_set_count(series_text: str) -> int | None:
    """Só deduz séries em prescrições simples. Protocolos especiais pedem confirmação."""
    normalized = series_text.lower().strip()
    special_tokens = ("+", "ciclo", "cluster", "bi-set", "tri set", "fst")
    if any(token in normalized for token in special_tokens):
        return None
    match = re.match(r"^(\d+)\s*x", normalized)
    if not match:
        return None
    value = int(match.group(1))
    return value if 1 <= value <= 20 else None


def _substitution_for(week: int, day: str, exercise_name: str) -> str | None:
    for row in exercise_logs(week, day):
        if row["exercise_name"] == exercise_name and row["substituted_by"]:
            return str(row["substituted_by"])
    return None


def _cleanup(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "series_exercises",
        "series_target",
        "series_total",
        "series_current",
        "series_load",
        "history_names",
    ):
        context.user_data.pop(key, None)


async def series_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    state = get_state()
    if not state["active"]:
        await update.message.reply_text("O protocolo ainda não começou.", reply_markup=ACTIVE_PROTOCOL_KEYBOARD)
        return ConversationHandler.END

    week = int(state["current_week"])
    day = _today_name()
    exercises = _today_exercises(week)
    if not exercises:
        await update.message.reply_text("Hoje não há treino previsto no protocolo.", reply_markup=ACTIVE_PROTOCOL_KEYBOARD)
        return ConversationHandler.END

    context.user_data["series_exercises"] = exercises
    await update.message.reply_text(
        "🏋️ *Registro série por série*\n\nQual exercício você está fazendo? Digite o número:\n\n" + _listing(exercises),
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return SERIES_EXERCISE


async def series_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        _cleanup(context)
        await update.message.reply_text("Registro cancelado.", reply_markup=ACTIVE_PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    if not text.isdigit():
        await update.message.reply_text("Digite apenas o número do exercício ou cancele.")
        return SERIES_EXERCISE

    exercises = context.user_data.get("series_exercises", [])
    index = int(text) - 1
    if index < 0 or index >= len(exercises):
        await update.message.reply_text("Esse número não está no treino de hoje.")
        return SERIES_EXERCISE

    target = exercises[index]
    context.user_data["series_target"] = target
    count = _simple_set_count(target["series"])
    if count is None:
        await update.message.reply_text(
            f"*{target['name']}*\nPrescrição original: `{target['series']}`\n\n"
            "Essa prescrição é especial/complexa. Quantas séries efetivamente vamos registrar hoje?",
            parse_mode="Markdown",
            reply_markup=CANCEL_KEYBOARD,
        )
        return SERIES_COUNT

    context.user_data["series_total"] = count
    context.user_data["series_current"] = 1
    return await _ask_load(update, context)


async def series_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        _cleanup(context)
        await update.message.reply_text("Registro cancelado.", reply_markup=ACTIVE_PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    if not text.isdigit() or not (1 <= int(text) <= 20):
        await update.message.reply_text("Informe um número de séries entre 1 e 20.")
        return SERIES_COUNT

    context.user_data["series_total"] = int(text)
    context.user_data["series_current"] = 1
    return await _ask_load(update, context)


async def _ask_load(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target = context.user_data["series_target"]
    current = context.user_data["series_current"]
    total = context.user_data["series_total"]
    state = get_state()
    week = int(state["current_week"])
    day = _today_name()
    substitute = _substitution_for(week, day, target["name"])
    performed = substitute or target["name"]

    previous = set_logs(week, day, target["name"])
    previous_row = next((row for row in previous if int(row["set_number"]) == current), None)
    previous_text = ""
    if previous_row:
        previous_text = f"\nAtual: carga `{previous_row['load'] or '-'}` / reps `{previous_row['reps'] or '-'}`"

    await update.message.reply_text(
        f"🏋️ *{performed}*\nSérie *{current}/{total}*{previous_text}\n\n"
        "Qual foi a carga? Ex.: `40 kg`, `20 kg cada lado`, `peso corporal` ou `-`.",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return SERIES_LOAD


async def series_load(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        _cleanup(context)
        await update.message.reply_text("Registro interrompido. As séries já salvas continuam guardadas.", reply_markup=ACTIVE_PROTOCOL_KEYBOARD)
        return ConversationHandler.END

    context.user_data["series_load"] = None if text == "-" else text
    current = context.user_data["series_current"]
    total = context.user_data["series_total"]
    await update.message.reply_text(
        f"Série *{current}/{total}*: quantas repetições você realizou?\n"
        "Pode usar `10`, `8-8`, `falha`, `7x3` etc., conforme a técnica da ficha.",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return SERIES_REPS


async def series_reps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        _cleanup(context)
        await update.message.reply_text("Registro interrompido. As séries já salvas continuam guardadas.", reply_markup=ACTIVE_PROTOCOL_KEYBOARD)
        return ConversationHandler.END

    state = get_state()
    week = int(state["current_week"])
    day = _today_name()
    target = context.user_data["series_target"]
    current = int(context.user_data["series_current"])
    total = int(context.user_data["series_total"])
    load = context.user_data.get("series_load")
    substitute = _substitution_for(week, day, target["name"])

    log_set(
        week=week,
        weekday=day,
        exercise_name=target["name"],
        performed_exercise=substitute,
        set_number=current,
        load=load,
        reps=text,
    )

    if current < total:
        context.user_data["series_current"] = current + 1
        context.user_data.pop("series_load", None)
        return await _ask_load(update, context)

    log_exercise(
        week,
        day,
        target["name"],
        result=f"{total} série(s) registradas",
        status="feito",
        substituted_by=substitute,
    )
    performed = substitute or target["name"]
    _cleanup(context)
    await update.message.reply_text(
        f"✅ *{performed}* concluído. Registrei as {total} séries separadamente.",
        parse_mode="Markdown",
        reply_markup=ACTIVE_PROTOCOL_KEYBOARD,
    )
    return ConversationHandler.END


async def history_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    names = logged_exercise_names()
    if not names:
        await update.message.reply_text(
            "Ainda não há séries registradas para comparar. Quando começarmos a salvar cargas e repetições, o histórico aparece aqui.",
            reply_markup=ACTIVE_PROTOCOL_KEYBOARD,
        )
        return ConversationHandler.END

    context.user_data["history_names"] = names
    listing = "\n".join(f"{i}. {name}" for i, name in enumerate(names, 1))
    await update.message.reply_text(
        "📊 *Histórico de carga*\n\nQual exercício você quer comparar?\n\n" + listing,
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return HISTORY_EXERCISE


async def history_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        _cleanup(context)
        await update.message.reply_text("Consulta cancelada.", reply_markup=ACTIVE_PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    if not text.isdigit():
        await update.message.reply_text("Digite o número do exercício ou cancele.")
        return HISTORY_EXERCISE

    names = context.user_data.get("history_names", [])
    index = int(text) - 1
    if index < 0 or index >= len(names):
        await update.message.reply_text("Esse número não está na lista.")
        return HISTORY_EXERCISE

    name = names[index]
    rows = exercise_history(name)
    grouped: dict[tuple[int, str, str], list] = defaultdict(list)
    for row in rows:
        performed = row["performed_exercise"] or row["exercise_name"]
        grouped[(int(row["week"]), str(row["weekday"]), str(performed))].append(row)

    parts = [f"📊 *Histórico — {name}*", ""]
    for (week, weekday, performed), sets in grouped.items():
        title = f"*Semana {week} — {weekday.capitalize()}*"
        if performed.lower() != name.lower():
            title += f"\n🔁 realizado como {performed}"
        parts.append(title)
        for row in sets:
            parts.append(
                f"• {int(row['set_number'])}ª série — {row['load'] or 'sem carga'} × {row['reps'] or '-'} rep"
            )
        parts.append("")

    if len(grouped) > 1:
        parts.append("↔️ Compare as semanas acima para acompanhar carga e repetições. O Butler preserva cada série individualmente.")
    else:
        parts.append("Ainda existe apenas um registro desse exercício; a comparação cresce conforme as semanas avançarem.")

    _cleanup(context)
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=ACTIVE_PROTOCOL_KEYBOARD)
    return ConversationHandler.END


def register_protocol_mass_series(application) -> None:
    series_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🏋️ Registrar séries$"), series_start)],
        states={
            SERIES_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_exercise)],
            SERIES_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_count)],
            SERIES_LOAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_load)],
            SERIES_REPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_reps)],
        },
        fallbacks=[],
    )
    history_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📊 Histórico de carga$"), history_start)],
        states={HISTORY_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, history_exercise)]},
        fallbacks=[],
    )
    application.add_handler(series_conv, group=-5)
    application.add_handler(history_conv, group=-5)
