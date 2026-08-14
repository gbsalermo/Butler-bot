from datetime import date, datetime

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationHandlerStop, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.assistant_state import (
    add_goal_progress,
    add_routine,
    complete_routine,
    goal_progress_totals,
    is_day_off,
    list_routines,
    set_day_off,
)
from src.home_store import list_goals

ROUTINE_NAME, ROUTINE_CATEGORY, ROUTINE_TIME, ROUTINE_DAYS, ROUTINE_REMINDER = range(300, 305)
ROUTINE_COMPLETE = 306
GOAL_PROGRESS_ID, GOAL_PROGRESS_AMOUNT, GOAL_PROGRESS_NOTE = range(310, 313)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["🌙 Day-off"], ["📚 Matérias", "✅ Tarefas"], ["📅 Compromissos", "📌 Pendências"],
     ["🏠 Cotidiano", "🗓️ Hoje"], ["💰 Finanças"]], resize_keyboard=True
)
HOME_KEYBOARD = ReplyKeyboardMarkup(
    [["🛒 O que está faltando?", "➕ Item faltando"], ["🎯 Metas", "🏋️ Musculação"],
     ["🧘 Rotinas", "🏠 Menu principal"]], resize_keyboard=True
)
ROUTINE_KEYBOARD = ReplyKeyboardMarkup(
    [["➕ Nova rotina", "📋 Ver rotinas"], ["✅ Cumpri uma rotina", "⬅️ Voltar ao cotidiano"]], resize_keyboard=True
)
GOAL_KEYBOARD = ReplyKeyboardMarkup(
    [["➕ Nova meta", "📋 Ver metas"], ["📈 Registrar progresso", "📊 Progresso das metas"],
     ["⬅️ Voltar ao cotidiano"]], resize_keyboard=True
)

WAKE_PHRASES = {
    "chamar, butler!", "chamar butler!", "butler, preciso de você!", "butler, preciso de voce!",
    "butler preciso de você", "butler preciso de voce", "butler, preciso de você", "butler, preciso de voce",
}


async def dayoff_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = (update.message.text or "").strip()
    lowered = text.lower()

    if text == "🌙 Day-off" or lowered in {"day-off", "day off"}:
        set_day_off(True)
        await update.message.reply_text(
            "🌙 Tudo bem. Hoje eu paro de cobrar, lembrar e organizar.\n\n"
            "Fica tranquilo. Quando quiser que eu volte, é só me chamar com *Butler, preciso de você!*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🕴️ Butler, preciso de você!"]], resize_keyboard=True),
        )
        raise ApplicationHandlerStop

    normalized_wake = lowered.replace("🕴️ ", "")
    if normalized_wake in WAKE_PHRASES:
        set_day_off(False)
        await update.message.reply_text(
            "🕴️ Estou aqui. O que precisamos colocar em ordem?",
            reply_markup=MAIN_KEYBOARD,
        )
        raise ApplicationHandlerStop

    if is_day_off():
        await update.message.reply_text(
            "🌙 Estou de folga com você hoje. Se precisar de mim, diga *Butler, preciso de você!*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🕴️ Butler, preciso de você!"]], resize_keyboard=True),
        )
        raise ApplicationHandlerStop


async def cotidiano_plus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🏠 *Cotidiano*\n\nO que eu posso tirar da sua cabeça agora?",
        parse_mode="Markdown", reply_markup=HOME_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def goals_plus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎯 *Metas*\n\nAlém de guardar suas metas, eu posso registrar o progresso para você enxergar constância em água, alimentação, inglês, programação, musculação, dinheiro e outras áreas.",
        parse_mode="Markdown", reply_markup=GOAL_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def routines_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🧘 *Rotinas e autocuidado*\n\nAqui entram coisas recorrentes como água, remédio, refeições, sono, inglês, programação ou qualquer hábito que você queira manter por perto.",
        parse_mode="Markdown", reply_markup=ROUTINE_KEYBOARD,
    )


async def routine_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["routine"] = {}
    await update.message.reply_text("Qual rotina quer criar? Ex.: `Beber água`, `Tomar remédio`, `Estudar inglês`.", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    return ROUTINE_NAME


async def routine_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["routine"]["name"] = (update.message.text or "").strip()
    await update.message.reply_text("Categoria? Ex.: `água`, `saúde`, `alimentação`, `sono`, `inglês`, `programação`.", parse_mode="Markdown")
    return ROUTINE_CATEGORY


async def routine_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["routine"]["category"] = (update.message.text or "").strip()
    await update.message.reply_text("Horário? Use `HH:MM` ou `sem horário`.", parse_mode="Markdown")
    return ROUTINE_TIME


async def routine_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lower()
    if value in {"sem horário", "sem horario", "-"}:
        parsed = None
    else:
        try: parsed = datetime.strptime(value, "%H:%M").strftime("%H:%M")
        except ValueError:
            await update.message.reply_text("Use `HH:MM` ou `sem horário`.", parse_mode="Markdown"); return ROUTINE_TIME
    context.user_data["routine"]["time"] = parsed
    await update.message.reply_text("Quais dias? Ex.: `seg, ter, qua, qui, sex` ou `todos`.", parse_mode="Markdown")
    return ROUTINE_DAYS


async def routine_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["routine"]["days"] = (update.message.text or "").strip().lower()
    if context.user_data["routine"].get("time"):
        await update.message.reply_text("Quantos minutos antes quer que eu avise? `0` para avisar na hora.", parse_mode="Markdown")
        return ROUTINE_REMINDER
    context.user_data["routine"]["reminder"] = 0
    return await _save_routine(update, context)


async def routine_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if not value.isdigit() or int(value) > 1440:
        await update.message.reply_text("Informe minutos entre 0 e 1440."); return ROUTINE_REMINDER
    context.user_data["routine"]["reminder"] = int(value)
    return await _save_routine(update, context)


async def _save_routine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("routine")
    add_routine(data["name"], data["category"], data.get("time"), data.get("days"), data.get("reminder", 0))
    await update.message.reply_text("🧘 Rotina salva. Eu vou considerar isso parte do seu cotidiano.", reply_markup=ROUTINE_KEYBOARD)
    return ConversationHandler.END


async def routines_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_routines()
    if not rows:
        await update.message.reply_text("Ainda não há rotinas cadastradas.", reply_markup=ROUTINE_KEYBOARD); return
    parts = ["🧘 *Suas rotinas*\n"]
    for r in rows:
        when = f" — {r['time_hhmm']}" if r["time_hhmm"] else ""
        days = f" — {r['weekdays']}" if r["weekdays"] else ""
        parts.append(f"`#{r['id']}` *{r['name']}* [{r['category']}]{when}{days}")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=ROUTINE_KEYBOARD)


async def routine_complete_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rows = list_routines()
    if not rows:
        await update.message.reply_text("Não há rotinas cadastradas.", reply_markup=ROUTINE_KEYBOARD); return ConversationHandler.END
    text = "\n".join(f"#{r['id']} — {r['name']}" for r in rows)
    await update.message.reply_text(f"Qual você cumpriu?\n\n{text}", reply_markup=ReplyKeyboardRemove())
    return ROUTINE_COMPLETE


async def routine_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lstrip("#")
    if not value.isdigit():
        await update.message.reply_text("Digite o número da rotina."); return ROUTINE_COMPLETE
    complete_routine(int(value), date.today().isoformat())
    await update.message.reply_text("✅ Registrado. Mais uma coisa feita hoje.", reply_markup=ROUTINE_KEYBOARD)
    return ConversationHandler.END


async def goal_progress_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rows = list_goals()
    if not rows:
        await update.message.reply_text("Cadastre uma meta primeiro.", reply_markup=GOAL_KEYBOARD); return ConversationHandler.END
    text = "\n".join(f"#{r['id']} — {r['name']}" for r in rows)
    await update.message.reply_text(f"Em qual meta quer registrar progresso?\n\n{text}", reply_markup=ReplyKeyboardRemove())
    return GOAL_PROGRESS_ID


async def goal_progress_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lstrip("#")
    if not value.isdigit():
        await update.message.reply_text("Digite o número da meta."); return GOAL_PROGRESS_ID
    context.user_data["goal_progress"] = {"goal_id": int(value)}
    await update.message.reply_text("Quanto você avançou? Informe apenas o número. Ex.: `2`, `1.5`, `30`.", parse_mode="Markdown")
    return GOAL_PROGRESS_AMOUNT


async def goal_progress_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try: amount = float((update.message.text or "").strip().replace(",", "."))
    except ValueError:
        await update.message.reply_text("Informe um número válido."); return GOAL_PROGRESS_AMOUNT
    context.user_data["goal_progress"]["amount"] = amount
    await update.message.reply_text("Quer deixar uma observação? `-` se não.", parse_mode="Markdown")
    return GOAL_PROGRESS_NOTE


async def goal_progress_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("goal_progress")
    note = (update.message.text or "").strip()
    add_goal_progress(data["goal_id"], data["amount"], None if note == "-" else note, date.today().isoformat())
    await update.message.reply_text("📈 Progresso registrado.", reply_markup=GOAL_KEYBOARD)
    return ConversationHandler.END


async def goals_progress_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = goal_progress_totals()
    if not rows:
        await update.message.reply_text("Ainda não há metas ativas.", reply_markup=GOAL_KEYBOARD); return
    parts = ["📊 *Progresso das metas*\n"]
    for r in rows:
        if r["target_value"]:
            pct = min(100, (float(r["progress"]) / float(r["target_value"])) * 100)
            parts.append(f"• *{r['name']}*: {r['progress']:g}/{r['target_value']:g} {r['target_unit'] or ''} — {pct:.0f}%")
        else:
            parts.append(f"• *{r['name']}*: {r['progress']:g} registrado")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=GOAL_KEYBOARD)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("routine", None); context.user_data.pop("goal_progress", None)
    await update.message.reply_text("Tudo bem, cancelei.", reply_markup=HOME_KEYBOARD)
    return ConversationHandler.END


def register_wellbeing_handlers(application) -> None:
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, dayoff_guard), group=-10)
    application.add_handler(MessageHandler(filters.Regex(r"^🏠 Cotidiano$"), cotidiano_plus), group=-4)
    application.add_handler(MessageHandler(filters.Regex(r"^🎯 Metas$"), goals_plus), group=-4)
    application.add_handler(MessageHandler(filters.Regex(r"^🧘 Rotinas$"), routines_menu), group=-4)
    application.add_handler(MessageHandler(filters.Regex(r"^📋 Ver rotinas$"), routines_list), group=-4)
    application.add_handler(MessageHandler(filters.Regex(r"^📊 Progresso das metas$"), goals_progress_view), group=-4)

    routine_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ Nova rotina$"), routine_add_start)],
        states={ROUTINE_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, routine_name)], ROUTINE_CATEGORY:[MessageHandler(filters.TEXT & ~filters.COMMAND, routine_category)], ROUTINE_TIME:[MessageHandler(filters.TEXT & ~filters.COMMAND, routine_time)], ROUTINE_DAYS:[MessageHandler(filters.TEXT & ~filters.COMMAND, routine_days)], ROUTINE_REMINDER:[MessageHandler(filters.TEXT & ~filters.COMMAND, routine_reminder)]},
        fallbacks=[CommandHandler("cancelar", cancel)])
    routine_done = ConversationHandler(entry_points=[MessageHandler(filters.Regex(r"^✅ Cumpri uma rotina$"), routine_complete_start)], states={ROUTINE_COMPLETE:[MessageHandler(filters.TEXT & ~filters.COMMAND, routine_complete)]}, fallbacks=[CommandHandler("cancelar", cancel)])
    progress_conv = ConversationHandler(entry_points=[MessageHandler(filters.Regex(r"^📈 Registrar progresso$"), goal_progress_start)], states={GOAL_PROGRESS_ID:[MessageHandler(filters.TEXT & ~filters.COMMAND, goal_progress_id)], GOAL_PROGRESS_AMOUNT:[MessageHandler(filters.TEXT & ~filters.COMMAND, goal_progress_amount)], GOAL_PROGRESS_NOTE:[MessageHandler(filters.TEXT & ~filters.COMMAND, goal_progress_note)]}, fallbacks=[CommandHandler("cancelar", cancel)])
    application.add_handler(routine_conv, group=-4); application.add_handler(routine_done, group=-4); application.add_handler(progress_conv, group=-4)
