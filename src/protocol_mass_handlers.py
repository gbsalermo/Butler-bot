import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from src.protocol_mass_data import SUBSTITUTIONS, WEEKS
from src.protocol_mass_store import begin_today, complete_today, completed_days, get_state, start_protocol

SUBSTITUTE_SELECT = 500

WEEKDAY = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

PROTOCOL_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🚀 Começar os trabalhos", "📅 Treino de hoje"],
        ["✅ Finalizar treino", "📈 Progresso Protocol Mass"],
        ["🔁 Substitutos", "⬅️ Voltar à musculação"],
    ],
    resize_keyboard=True,
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup([["❌ Cancelar ação"]], resize_keyboard=True)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return " ".join(text.split())


def _week_data(week: int) -> dict:
    return WEEKS.get(str(week), {})


def _today_name() -> str:
    return WEEKDAY[date.today().weekday()]


def _today_exercises(week: int) -> list[dict]:
    return _week_data(week).get(_today_name(), [])


def _find_substitutes(exercise_name: str) -> tuple[str | None, list[str]]:
    target = _normalize(exercise_name)
    exact = next((name for name in SUBSTITUTIONS if _normalize(name) == target), None)
    if exact:
        return exact, SUBSTITUTIONS[exact]

    best_name = None
    best_score = 0.0
    for name in SUBSTITUTIONS:
        score = SequenceMatcher(None, target, _normalize(name)).ratio()
        if score > best_score:
            best_name, best_score = name, score
    if best_name and best_score >= 0.62:
        return best_name, SUBSTITUTIONS[best_name]
    return None, []


def _format_exercise(index: int, exercise: dict) -> str:
    parts = [f"{index}. *{exercise['name']}* — {exercise['series']}"]
    details = []
    if exercise.get("interval"):
        details.append(f"descanso {exercise['interval']}")
    if exercise.get("velocity"):
        details.append(f"vel. {exercise['velocity']}")
    if exercise.get("technique") and exercise["technique"] != "-":
        details.append(exercise["technique"])
    if details:
        parts.append("   " + " • ".join(details))
    return "\n".join(parts)


async def protocol_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🏋️ *Protocol Mass*\n\n"
        "Tenho as 12 semanas do protocolo salvas. Quando você decidir iniciar, use *🚀 Começar os trabalhos*. "
        "A partir daí eu acompanho os dias cumpridos e só avanço a semana quando os seis treinos forem concluídos.",
        parse_mode="Markdown",
        reply_markup=PROTOCOL_KEYBOARD,
    )


async def start_work(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_before = get_state()
    state = start_protocol()
    week = int(state["current_week"])
    day = _today_name()

    if day == "domingo":
        await update.message.reply_text(
            f"🚀 *Os trabalhos estão valendo.*\n\nSemana atual: *{week}*. Hoje é domingo, então não há treino previsto no protocolo. Amanhã seguimos pela segunda-feira.",
            parse_mode="Markdown",
            reply_markup=PROTOCOL_KEYBOARD,
        )
        return

    begin_today(week, day)
    intro = "🚀 *Começamos os trabalhos.*" if not state_before["active"] else "🕴️ *De volta ao trabalho.*"
    await update.message.reply_text(
        f"{intro}\n\nSemana *{week}/12* — {day.capitalize()}. Vou considerar o treino de hoje como iniciado.",
        parse_mode="Markdown",
        reply_markup=PROTOCOL_KEYBOARD,
    )
    await show_today(update, context)


async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = get_state()
    if not state["active"]:
        await update.message.reply_text(
            "O Protocol Mass ainda não foi iniciado. Quando for a hora, me diga *🚀 Começar os trabalhos*.",
            parse_mode="Markdown",
            reply_markup=PROTOCOL_KEYBOARD,
        )
        return

    week = int(state["current_week"])
    day = _today_name()
    if day == "domingo":
        await update.message.reply_text("😴 Hoje não há treino previsto: domingo é descanso no protocolo.", reply_markup=PROTOCOL_KEYBOARD)
        return

    exercises = _today_exercises(week)
    if not exercises:
        await update.message.reply_text(
            f"Não encontrei treino cadastrado para {day} na Semana {week}. Não vou inventar uma ficha; esse ponto precisa ser conferido na planilha original.",
            reply_markup=PROTOCOL_KEYBOARD,
        )
        return

    done = day in completed_days(week)
    parts = [f"🏋️ *Protocol Mass — Semana {week}/12*", f"📅 *{day.capitalize()}*", ""]
    for i, exercise in enumerate(exercises, 1):
        parts.append(_format_exercise(i, exercise))
    parts.append("\n✅ Esse treino já foi concluído nesta semana." if done else "\nQuando terminar, use *✅ Finalizar treino*.")
    parts.append("Se algum exercício não der para fazer, use *🔁 Substitutos* e escolha o número dele.")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=PROTOCOL_KEYBOARD)


async def finish_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = get_state()
    if not state["active"]:
        await update.message.reply_text("Ainda não começamos o protocolo.", reply_markup=PROTOCOL_KEYBOARD)
        return
    week = int(state["current_week"])
    day = _today_name()
    if day == "domingo":
        await update.message.reply_text("Domingo não entra na contagem dos seis treinos da semana.", reply_markup=PROTOCOL_KEYBOARD)
        return
    if day not in _week_data(week):
        await update.message.reply_text("Não há treino cadastrado para hoje.", reply_markup=PROTOCOL_KEYBOARD)
        return

    completed, next_week, advanced = complete_today(week, day)
    if advanced:
        text = f"✅ *Semana {week} concluída: 6/6.*\n\nBoa. A próxima etapa já está liberada: *Semana {next_week}/12*."
    elif week == 12 and completed >= 6:
        text = "🏁 *Protocol Mass concluído.*\n\nAs 12 semanas foram fechadas."
    else:
        text = f"✅ Treino de {day} concluído.\n\n📈 Semana {week}: *{completed}/6 treinos feitos*."
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=PROTOCOL_KEYBOARD)


async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = get_state()
    week = int(state["current_week"])
    done = completed_days(week)
    marks = []
    for day in ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"]:
        marks.append(f"{'✅' if day in done else '⬜'} {day.capitalize()}")
    status = "ativo" if state["active"] else ("concluído" if state["finished_at"] else "ainda não iniciado")
    await update.message.reply_text(
        f"📈 *Protocol Mass*\n\nStatus: *{status}*\nSemana atual: *{week}/12*\nCumprimento: *{len(done)}/6*\n\n" + "\n".join(marks),
        parse_mode="Markdown",
        reply_markup=PROTOCOL_KEYBOARD,
    )


async def substitutes_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    state = get_state()
    if not state["active"]:
        await update.message.reply_text("Primeiro precisamos iniciar o protocolo.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    exercises = _today_exercises(int(state["current_week"]))
    if not exercises:
        await update.message.reply_text("Hoje não há treino previsto.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    context.user_data["protocol_sub_exercises"] = exercises
    listing = "\n".join(f"{i}. {ex['name']}" for i, ex in enumerate(exercises, 1))
    await update.message.reply_text(
        "Qual exercício você precisa substituir? Digite o número:\n\n" + listing,
        reply_markup=CANCEL_KEYBOARD,
    )
    return SUBSTITUTE_SELECT


async def substitute_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        context.user_data.pop("protocol_sub_exercises", None)
        await update.message.reply_text("Tudo bem, mantemos o treino como está.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    if not text.isdigit():
        await update.message.reply_text("Digite apenas o número do exercício ou cancele.")
        return SUBSTITUTE_SELECT
    exercises = context.user_data.get("protocol_sub_exercises", [])
    index = int(text) - 1
    if index < 0 or index >= len(exercises):
        await update.message.reply_text("Esse número não está na ficha de hoje.")
        return SUBSTITUTE_SELECT
    exercise = exercises[index]
    matched, alternatives = _find_substitutes(exercise["name"])
    context.user_data.pop("protocol_sub_exercises", None)
    if not alternatives:
        await update.message.reply_text(
            f"Não achei um substituto oficial na tabela para *{exercise['name']}*. Prefiro não inventar um.",
            parse_mode="Markdown",
            reply_markup=PROTOCOL_KEYBOARD,
        )
        return ConversationHandler.END
    lines = [f"🔁 *{exercise['name']}*", "", "Substitutos previstos na tabela:"]
    for alt in alternatives:
        lines.append(f"• {alt}")
    if matched and _normalize(matched) != _normalize(exercise["name"]):
        lines.append(f"\n_Referência localizada como: {matched}_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=PROTOCOL_KEYBOARD)
    return ConversationHandler.END


def register_protocol_mass_handlers(application) -> None:
    substitute_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🔁 Substitutos$"), substitutes_start)],
        states={SUBSTITUTE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, substitute_select)]},
        fallbacks=[],
    )
    application.add_handler(substitute_conv, group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^🚀 Começar os trabalhos$"), start_work), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^📅 Treino de hoje$"), show_today), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^✅ Finalizar treino$"), finish_today), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^📈 Progresso Protocol Mass$"), progress), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^⬅️ Voltar à musculação$"), protocol_menu), group=-2)
