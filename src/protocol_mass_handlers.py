import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from src.protocol_mass_data import SUBSTITUTIONS, WEEKS
from src.protocol_mass_store import (
    begin_today,
    complete_today,
    completed_days,
    exercise_logs,
    get_state,
    log_exercise,
    reset_protocol,
    skip_today,
    skipped_days,
    start_protocol,
)

SUBSTITUTE_SELECT, SUBSTITUTE_CHOICE = range(500, 502)
LOG_SELECT, LOG_RESULT = range(510, 512)
SKIP_REASON = 520
RESET_CONFIRM = 530

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
        ["📝 Registrar exercício", "🔁 Substituir exercício"],
        ["✅ Finalizar treino", "😕 Não consegui treinar hoje"],
        ["📈 Progresso Protocol Mass", "🧪 Exemplo de treino"],
        ["🔄 Reiniciar os trabalhos"],
        ["⬅️ Voltar à musculação"],
    ],
    resize_keyboard=True,
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup([["❌ Cancelar ação"]], resize_keyboard=True)
SKIP_KEYBOARD = ReplyKeyboardMarkup([["Sem motivo específico"], ["❌ Cancelar ação"]], resize_keyboard=True)
RESET_KEYBOARD = ReplyKeyboardMarkup([["✅ Sim, reiniciar", "❌ Não"]], resize_keyboard=True)


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


def _format_exercise(index: int, exercise: dict, log: dict | None = None) -> str:
    prefix = ""
    if log:
        if log.get("status") == "substituido":
            prefix = "🔁 "
        else:
            prefix = "✅ "
    parts = [f"{index}. {prefix}*{exercise['name']}* — {exercise['series']}"]
    details = []
    if exercise.get("interval"):
        details.append(f"descanso {exercise['interval']}")
    if exercise.get("velocity"):
        details.append(f"vel. {exercise['velocity']}")
    if exercise.get("technique") and exercise["technique"] != "-":
        details.append(exercise["technique"])
    if details:
        parts.append("   " + " • ".join(details))
    if log:
        if log.get("substituted_by"):
            parts.append(f"   ↳ substituído por: {log['substituted_by']}")
        if log.get("result"):
            parts.append(f"   📝 resultado: {log['result']}")
    return "\n".join(parts)


def _logs_by_name(week: int, day: str) -> dict[str, dict]:
    return {row["exercise_name"]: dict(row) for row in exercise_logs(week, day)}


def _exercise_listing(exercises: list[dict]) -> str:
    return "\n".join(f"{i}. {ex['name']}" for i, ex in enumerate(exercises, 1))


async def protocol_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🏋️ *Protocol Mass*\n\n"
        "Tenho as 12 semanas do protocolo salvas. Use *🚀 Começar os trabalhos* para iniciar ou retomar. "
        "Eu acompanho dias cumpridos, exercícios registrados, substituições e também os dias em que não deu para treinar.",
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
            f"🚀 *Os trabalhos estão valendo.*\n\nSemana atual: *{week}*. Hoje é domingo, então não há treino previsto no protocolo.",
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
            "O Protocol Mass ainda não foi iniciado. Quando for a hora, use *🚀 Começar os trabalhos*.",
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
            f"Não encontrei treino cadastrado para {day} na Semana {week}. Não vou inventar uma ficha.",
            reply_markup=PROTOCOL_KEYBOARD,
        )
        return

    done = day in completed_days(week)
    skipped = skipped_days(week)
    logs = _logs_by_name(week, day)
    parts = [f"🏋️ *Protocol Mass — Semana {week}/12*", f"📅 *{day.capitalize()}*", ""]
    for i, exercise in enumerate(exercises, 1):
        parts.append(_format_exercise(i, exercise, logs.get(exercise["name"])))

    if done:
        parts.append("\n✅ Esse treino já foi concluído nesta semana.")
    elif day in skipped:
        reason = skipped[day]
        extra = f" Motivo: {reason}." if reason else ""
        parts.append(f"\n😕 Hoje ficou registrado como treino não realizado.{extra}")
    else:
        parts.append("\nUse *📝 Registrar exercício* conforme for avançando e *✅ Finalizar treino* quando terminar.")
    parts.append("Se precisar trocar um movimento, use *🔁 Substituir exercício*.")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=PROTOCOL_KEYBOARD)


async def log_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    state = get_state()
    if not state["active"]:
        await update.message.reply_text("Primeiro precisamos iniciar os trabalhos.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    week = int(state["current_week"])
    exercises = _today_exercises(week)
    if not exercises:
        await update.message.reply_text("Hoje não há treino previsto.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    context.user_data["protocol_log_exercises"] = exercises
    await update.message.reply_text(
        "Qual exercício você acabou de fazer? Digite o número:\n\n" + _exercise_listing(exercises),
        reply_markup=CANCEL_KEYBOARD,
    )
    return LOG_SELECT


async def log_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        context.user_data.pop("protocol_log_exercises", None)
        await update.message.reply_text("Registro cancelado.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    if not text.isdigit():
        await update.message.reply_text("Digite o número do exercício ou cancele.")
        return LOG_SELECT
    exercises = context.user_data.get("protocol_log_exercises", [])
    index = int(text) - 1
    if index < 0 or index >= len(exercises):
        await update.message.reply_text("Esse número não está no treino de hoje.")
        return LOG_SELECT
    context.user_data["protocol_log_target"] = exercises[index]
    await update.message.reply_text(
        "Anote carga e repetições de forma curta.\nEx.: `40 kg — 10/9/8` ou `20 kg cada lado — 8/8/7`.\nSe só quiser marcar como feito, digite `feito`.",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return LOG_RESULT


async def log_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        context.user_data.pop("protocol_log_exercises", None)
        context.user_data.pop("protocol_log_target", None)
        await update.message.reply_text("Registro cancelado.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    exercise = context.user_data.pop("protocol_log_target")
    context.user_data.pop("protocol_log_exercises", None)
    state = get_state()
    result = None if text.lower() == "feito" else text
    log_exercise(int(state["current_week"]), _today_name(), exercise["name"], result=result, status="feito")
    await update.message.reply_text(f"✅ {exercise['name']} registrado.", reply_markup=PROTOCOL_KEYBOARD)
    return ConversationHandler.END


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
    await update.message.reply_text(
        "Qual exercício você não conseguiu fazer? Digite o número:\n\n" + _exercise_listing(exercises),
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
    if not alternatives:
        context.user_data.pop("protocol_sub_exercises", None)
        await update.message.reply_text(
            f"Não achei um substituto oficial na tabela para *{exercise['name']}*. Prefiro não inventar um.",
            parse_mode="Markdown",
            reply_markup=PROTOCOL_KEYBOARD,
        )
        return ConversationHandler.END
    context.user_data["protocol_sub_target"] = exercise
    context.user_data["protocol_sub_alternatives"] = alternatives
    lines = [f"🔁 *{exercise['name']}*", "", "Qual substituto você vai usar?"]
    for i, alt in enumerate(alternatives, 1):
        lines.append(f"{i}. {alt}")
    if matched and _normalize(matched) != _normalize(exercise["name"]):
        lines.append(f"\n_Referência localizada como: {matched}_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=CANCEL_KEYBOARD)
    return SUBSTITUTE_CHOICE


async def substitute_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        for key in ("protocol_sub_exercises", "protocol_sub_target", "protocol_sub_alternatives"):
            context.user_data.pop(key, None)
        await update.message.reply_text("Substituição cancelada.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    if not text.isdigit():
        await update.message.reply_text("Digite o número do substituto ou cancele.")
        return SUBSTITUTE_CHOICE
    alternatives = context.user_data.get("protocol_sub_alternatives", [])
    index = int(text) - 1
    if index < 0 or index >= len(alternatives):
        await update.message.reply_text("Esse número não está entre os substitutos.")
        return SUBSTITUTE_CHOICE
    exercise = context.user_data.get("protocol_sub_target")
    alternative = alternatives[index]
    state = get_state()
    log_exercise(
        int(state["current_week"]),
        _today_name(),
        exercise["name"],
        status="substituido",
        substituted_by=alternative,
    )
    for key in ("protocol_sub_exercises", "protocol_sub_target", "protocol_sub_alternatives"):
        context.user_data.pop(key, None)
    await update.message.reply_text(
        f"🔁 Certo. Hoje *{exercise['name']}* foi substituído por *{alternative}*. Vou deixar isso registrado no treino.",
        parse_mode="Markdown",
        reply_markup=PROTOCOL_KEYBOARD,
    )
    return ConversationHandler.END


async def skip_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    state = get_state()
    if not state["active"]:
        await update.message.reply_text("Ainda não começamos os trabalhos.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    if _today_name() == "domingo":
        await update.message.reply_text("Hoje já é descanso previsto no protocolo.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    await update.message.reply_text(
        "Tudo bem. Quer registrar algum motivo? Pode escrever livremente ou escolher *Sem motivo específico*.",
        parse_mode="Markdown",
        reply_markup=SKIP_KEYBOARD,
    )
    return SKIP_REASON


async def skip_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        await update.message.reply_text("Certo, não alterei o treino de hoje.", reply_markup=PROTOCOL_KEYBOARD)
        return ConversationHandler.END
    reason = None if text == "Sem motivo específico" else text
    state = get_state()
    skip_today(int(state["current_week"]), _today_name(), reason)
    await update.message.reply_text(
        "😕 Anotado. Hoje não conta como treino concluído e a semana não avança por causa disso. Quando der, seguimos de onde paramos.",
        reply_markup=PROTOCOL_KEYBOARD,
    )
    return ConversationHandler.END


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
    skipped = skipped_days(week)
    marks = []
    for day in ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"]:
        if day in done:
            mark = "✅"
        elif day in skipped:
            mark = "➖"
        else:
            mark = "⬜"
        marks.append(f"{mark} {day.capitalize()}")
    status = "ativo" if state["active"] else ("concluído" if state["finished_at"] else "ainda não iniciado")
    await update.message.reply_text(
        f"📈 *Protocol Mass*\n\nStatus: *{status}*\nSemana atual: *{week}/12*\nCumprimento: *{len(done)}/6*\n\n"
        + "\n".join(marks)
        + "\n\n✅ feito • ➖ não treinado • ⬜ pendente",
        parse_mode="Markdown",
        reply_markup=PROTOCOL_KEYBOARD,
    )


async def example(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    exercises = WEEKS.get("1", {}).get("segunda-feira", [])
    lines = [
        "🧪 *Exemplo de fluxo — Semana 1 / Segunda-feira*",
        "",
        "Este exemplo não altera seu progresso real.",
        "",
    ]
    for i, exercise in enumerate(exercises[:4], 1):
        lines.append(_format_exercise(i, exercise))
    if len(exercises) > 4:
        lines.append(f"… + {len(exercises) - 4} exercício(s)")
    lines.extend(
        [
            "",
            "Durante o treino você poderia:",
            "• registrar `Pulley frente — 45 kg — 12/10/9`;",
            "• trocar um exercício usando *🔁 Substituir exercício*;",
            "• finalizar o dia normalmente;",
            "• ou marcar *😕 Não consegui treinar hoje*.",
            "",
            "Se quiser testar de verdade no banco, use *🚀 Começar os trabalhos*. Depois você pode zerar tudo com *🔄 Reiniciar os trabalhos*.",
        ]
    )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=PROTOCOL_KEYBOARD)


async def reset_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "⚠️ *Reiniciar os trabalhos?*\n\nEsta opção é temporária para os testes. Ela apaga todo o progresso do Protocol Mass, registros de exercícios e substituições, voltando para Semana 1 não iniciada.",
        parse_mode="Markdown",
        reply_markup=RESET_KEYBOARD,
    )
    return RESET_CONFIRM


async def reset_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if (update.message.text or "") == "✅ Sim, reiniciar":
        reset_protocol()
        await update.message.reply_text(
            "🔄 Protocol Mass zerado. Voltamos para antes do primeiro treino. Quando quiser, diga *🚀 Começar os trabalhos*.",
            parse_mode="Markdown",
            reply_markup=PROTOCOL_KEYBOARD,
        )
    else:
        await update.message.reply_text("Certo. Mantive seu progresso como estava.", reply_markup=PROTOCOL_KEYBOARD)
    return ConversationHandler.END


def register_protocol_mass_handlers(application) -> None:
    log_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📝 Registrar exercício$"), log_start)],
        states={
            LOG_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_select)],
            LOG_RESULT: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_result)],
        },
        fallbacks=[],
    )
    substitute_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🔁 Substituir exercício$"), substitutes_start)],
        states={
            SUBSTITUTE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, substitute_select)],
            SUBSTITUTE_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, substitute_choice)],
        },
        fallbacks=[],
    )
    skip_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^😕 Não consegui treinar hoje$"), skip_start)],
        states={SKIP_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, skip_reason)]},
        fallbacks=[],
    )
    reset_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🔄 Reiniciar os trabalhos$"), reset_start)],
        states={RESET_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_confirm)]},
        fallbacks=[],
    )

    application.add_handler(log_conv, group=-2)
    application.add_handler(substitute_conv, group=-2)
    application.add_handler(skip_conv, group=-2)
    application.add_handler(reset_conv, group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^🚀 Começar os trabalhos$"), start_work), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^📅 Treino de hoje$"), show_today), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^✅ Finalizar treino$"), finish_today), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^📈 Progresso Protocol Mass$"), progress), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^🧪 Exemplo de treino$"), example), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^⬅️ Voltar à musculação$"), protocol_menu), group=-2)
