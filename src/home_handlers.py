from collections import defaultdict

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.home_store import (
    add_goal,
    add_grocery_item,
    add_workout_exercise,
    list_goals,
    list_missing_groceries,
    list_workout,
    mark_grocery_bought,
)

GROCERY_NAME, GROCERY_QTY, GROCERY_NOTE, GROCERY_BOUGHT = range(200, 204)
GOAL_NAME, GOAL_CATEGORY, GOAL_TARGET, GOAL_PERIOD = range(210, 214)
WORKOUT_DAY, WORKOUT_FOCUS, WORKOUT_EXERCISE, WORKOUT_LOAD, WORKOUT_SETS, WORKOUT_REPS = range(220, 226)

HOME_KEYBOARD = ReplyKeyboardMarkup(
    [["🛒 O que está faltando?", "➕ Item faltando"], ["🎯 Metas", "🏋️ Musculação"], ["🏠 Menu principal"]],
    resize_keyboard=True,
)

GOALS_KEYBOARD = ReplyKeyboardMarkup(
    [["➕ Nova meta", "📋 Ver metas"], ["⬅️ Voltar ao cotidiano"]],
    resize_keyboard=True,
)

WORKOUT_KEYBOARD = ReplyKeyboardMarkup(
    [["➕ Adicionar exercício", "📋 Ver rotina"], ["⬅️ Voltar ao cotidiano"]],
    resize_keyboard=True,
)

WEEKDAYS = {
    "seg": "segunda-feira", "segunda": "segunda-feira", "segunda-feira": "segunda-feira",
    "ter": "terça-feira", "terça": "terça-feira", "terca": "terça-feira", "terça-feira": "terça-feira",
    "qua": "quarta-feira", "quarta": "quarta-feira", "quarta-feira": "quarta-feira",
    "qui": "quinta-feira", "quinta": "quinta-feira", "quinta-feira": "quinta-feira",
    "sex": "sexta-feira", "sexta": "sexta-feira", "sexta-feira": "sexta-feira",
    "sab": "sábado", "sábado": "sábado", "sabado": "sábado", "sábado": "sábado",
    "dom": "domingo", "domingo": "domingo",
}


async def cotidiano_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "🏠 *Cotidiano*\n\nAqui ficam coisas que o Butler deve manter na memória por você: itens faltando em casa, metas pessoais e sua rotina de musculação.",
            parse_mode="Markdown",
            reply_markup=HOME_KEYBOARD,
        )


async def list_groceries(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_missing_groceries()
    if not rows:
        await update.message.reply_text("🛒 Não há nada marcado como faltando em casa.", reply_markup=HOME_KEYBOARD)
        return
    parts = ["🛒 *O que está faltando em casa*\n"]
    for row in rows:
        qty = f" — {row['quantity']}" if row["quantity"] else ""
        note = f" ({row['note']})" if row["note"] else ""
        parts.append(f"`#{row['id']}` • {row['name']}{qty}{note}")
    parts.append("\nQuando comprar algo, use *✅ Marcar comprado*.")
    keyboard = ReplyKeyboardMarkup([["✅ Marcar comprado", "➕ Item faltando"], ["⬅️ Voltar ao cotidiano"]], resize_keyboard=True)
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=keyboard)


async def grocery_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["grocery"] = {}
    await update.message.reply_text("O que está faltando?", reply_markup=ReplyKeyboardRemove())
    return GROCERY_NAME


async def grocery_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if len(name) < 2:
        await update.message.reply_text("Informe um item válido.")
        return GROCERY_NAME
    context.user_data["grocery"]["name"] = name
    await update.message.reply_text("Quantidade/tamanho? Ex.: `2`, `1 kg`, `grande`. Digite `-` se não precisar.", parse_mode="Markdown")
    return GROCERY_QTY


async def grocery_qty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    context.user_data["grocery"]["quantity"] = None if value == "-" else value
    await update.message.reply_text("Alguma observação? Digite `-` se não houver.", parse_mode="Markdown")
    return GROCERY_NOTE


async def grocery_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    data = context.user_data.pop("grocery")
    add_grocery_item(data["name"], data.get("quantity"), None if value == "-" else value)
    await update.message.reply_text(f"✅ {data['name']} ficou salvo como faltando.", reply_markup=HOME_KEYBOARD)
    return ConversationHandler.END


async def grocery_bought_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rows = list_missing_groceries()
    if not rows:
        await update.message.reply_text("Não há itens faltando.", reply_markup=HOME_KEYBOARD)
        return ConversationHandler.END
    text = "\n".join(f"#{row['id']} — {row['name']}" for row in rows)
    await update.message.reply_text(f"Qual item você comprou? Digite o número.\n\n{text}", reply_markup=ReplyKeyboardRemove())
    return GROCERY_BOUGHT


async def grocery_bought(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lstrip("#")
    if not value.isdigit():
        await update.message.reply_text("Digite apenas o número do item.")
        return GROCERY_BOUGHT
    if mark_grocery_bought(int(value)):
        await update.message.reply_text("✅ Item retirado da lista de faltas.", reply_markup=HOME_KEYBOARD)
    else:
        await update.message.reply_text("Não encontrei esse item.", reply_markup=HOME_KEYBOARD)
    return ConversationHandler.END


async def goals_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎯 *Metas do Butler*\n\nMetas podem ser financeiras ou pessoais: água, alimentação, inglês, programação, musculação, estudos e outras áreas.",
        parse_mode="Markdown",
        reply_markup=GOALS_KEYBOARD,
    )


async def goal_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["goal"] = {}
    await update.message.reply_text("Qual é a meta?", reply_markup=ReplyKeyboardRemove())
    return GOAL_NAME


async def goal_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["goal"]["name"] = (update.message.text or "").strip()
    await update.message.reply_text("Categoria? Ex.: `água`, `alimentação`, `inglês`, `programação`, `musculação`, `financeiro`.", parse_mode="Markdown")
    return GOAL_CATEGORY


async def goal_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["goal"]["category"] = (update.message.text or "").strip()
    await update.message.reply_text("Qual alvo? Ex.: `2 litros`, `5 horas`, `300 reais`, `4 treinos`. Digite `-` se for apenas uma meta qualitativa.", parse_mode="Markdown")
    return GOAL_TARGET


async def goal_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    data = context.user_data["goal"]
    if value == "-":
        data["target_value"] = None
        data["target_unit"] = None
    else:
        pieces = value.replace(",", ".").split(maxsplit=1)
        try:
            data["target_value"] = float(pieces[0])
            data["target_unit"] = pieces[1] if len(pieces) > 1 else "unidades"
        except ValueError:
            await update.message.reply_text("Comece o alvo com um número, por exemplo `2 litros` ou use `-`.", parse_mode="Markdown")
            return GOAL_TARGET
    await update.message.reply_text("Periodicidade? Ex.: `por dia`, `por semana`, `por mês` ou uma data/meta livre.", parse_mode="Markdown")
    return GOAL_PERIOD


async def goal_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("goal")
    add_goal(data["name"], data["category"], data.get("target_value"), data.get("target_unit"), (update.message.text or "").strip())
    await update.message.reply_text("🎯 Meta salva.", reply_markup=GOALS_KEYBOARD)
    return ConversationHandler.END


async def goals_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_goals()
    if not rows:
        await update.message.reply_text("Você ainda não cadastrou metas.", reply_markup=GOALS_KEYBOARD)
        return
    parts = ["🎯 *Metas ativas*\n"]
    for row in rows:
        target = ""
        if row["target_value"] is not None:
            target = f" — {row['target_value']:g} {row['target_unit'] or ''}".rstrip()
        period = f" / {row['period']}" if row["period"] else ""
        parts.append(f"• *{row['name']}* [{row['category']}]{target}{period}")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=GOALS_KEYBOARD)


async def workout_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🏋️ *Musculação*\n\nSalve sua divisão semanal e, dentro de cada dia, os exercícios com carga, séries e repetições.",
        parse_mode="Markdown",
        reply_markup=WORKOUT_KEYBOARD,
    )


async def workout_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["workout"] = {}
    await update.message.reply_text("Qual dia? Ex.: `segunda`, `ter`, `quarta`.", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    return WORKOUT_DAY


async def workout_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.message.text or "").strip().lower()
    day = WEEKDAYS.get(raw)
    if not day:
        await update.message.reply_text("Não reconheci o dia. Tente `segunda`, `terça`, `quarta` etc.", parse_mode="Markdown")
        return WORKOUT_DAY
    context.user_data["workout"]["weekday"] = day
    await update.message.reply_text("Qual é o foco desse dia? Ex.: `peito`, `costas e bíceps`, `perna`.", parse_mode="Markdown")
    return WORKOUT_FOCUS


async def workout_focus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["workout"]["focus"] = (update.message.text or "").strip()
    await update.message.reply_text("Qual exercício deseja adicionar?")
    return WORKOUT_EXERCISE


async def workout_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["workout"]["exercise"] = (update.message.text or "").strip()
    await update.message.reply_text("Carga atual? Ex.: `20 kg`, `10 kg cada lado`, `peso corporal`. Use `-` se não quiser registrar.", parse_mode="Markdown")
    return WORKOUT_LOAD


async def workout_load(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    context.user_data["workout"]["load"] = None if value == "-" else value
    await update.message.reply_text("Quantas séries? Ex.: `4`.", parse_mode="Markdown")
    return WORKOUT_SETS


async def workout_sets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if not value.isdigit() or int(value) <= 0:
        await update.message.reply_text("Digite um número válido de séries.")
        return WORKOUT_SETS
    context.user_data["workout"]["sets"] = int(value)
    await update.message.reply_text("Repetições? Pode ser `12`, `8-10`, `até falha` etc.", parse_mode="Markdown")
    return WORKOUT_REPS


async def workout_reps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("workout")
    add_workout_exercise(data["weekday"], data["focus"], data["exercise"], data.get("load"), data["sets"], (update.message.text or "").strip())
    await update.message.reply_text("🏋️ Exercício salvo na rotina.", reply_markup=WORKOUT_KEYBOARD)
    return ConversationHandler.END


async def workout_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_workout()
    if not rows:
        await update.message.reply_text("Sua rotina de musculação ainda está vazia.", reply_markup=WORKOUT_KEYBOARD)
        return
    grouped = defaultdict(list)
    focuses = {}
    for row in rows:
        focuses[row["weekday"]] = row["focus"]
        if row["name"]:
            grouped[row["weekday"]].append(row)
    parts = ["🏋️ *Rotina de musculação*\n"]
    for day, focus in focuses.items():
        parts.append(f"*{day.capitalize()} — {focus}*")
        if not grouped[day]:
            parts.append("• Nenhum exercício cadastrado")
        for row in grouped[day]:
            detail = f"{row['sets']}x{row['reps']}" if row["sets"] else (row["reps"] or "")
            load = f" — {row['load']}" if row["load"] else ""
            parts.append(f"• {row['name']} — {detail}{load}")
        parts.append("")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=WORKOUT_KEYBOARD)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    for key in ("grocery", "goal", "workout"):
        context.user_data.pop(key, None)
    await update.message.reply_text("Operação cancelada.", reply_markup=HOME_KEYBOARD)
    return ConversationHandler.END


def register_home_handlers(application) -> None:
    grocery_add = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ Item faltando$"), grocery_add_start)],
        states={
            GROCERY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, grocery_name)],
            GROCERY_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, grocery_qty)],
            GROCERY_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, grocery_note)],
        }, fallbacks=[CommandHandler("cancelar", cancel)],
    )
    grocery_bought_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^✅ Marcar comprado$"), grocery_bought_start)],
        states={GROCERY_BOUGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, grocery_bought)]},
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    goal_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ Nova meta$"), goal_add_start)],
        states={
            GOAL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_name)],
            GOAL_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_category)],
            GOAL_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_target)],
            GOAL_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_period)],
        }, fallbacks=[CommandHandler("cancelar", cancel)],
    )
    workout_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ Adicionar exercício$"), workout_add_start)],
        states={
            WORKOUT_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, workout_day)],
            WORKOUT_FOCUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, workout_focus)],
            WORKOUT_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, workout_exercise)],
            WORKOUT_LOAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, workout_load)],
            WORKOUT_SETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, workout_sets)],
            WORKOUT_REPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, workout_reps)],
        }, fallbacks=[CommandHandler("cancelar", cancel)],
    )

    application.add_handler(grocery_add, group=-1)
    application.add_handler(grocery_bought_conv, group=-1)
    application.add_handler(goal_conv, group=-1)
    application.add_handler(workout_conv, group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^🏠 Cotidiano$"), cotidiano_menu), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^🛒 O que está faltando\?$"), list_groceries), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^🎯 Metas$"), goals_menu), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^📋 Ver metas$"), goals_list), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^🏋️ Musculação$"), workout_menu), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^📋 Ver rotina$"), workout_list), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^⬅️ Voltar ao cotidiano$"), cotidiano_menu), group=-1)
