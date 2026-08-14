import re
import sqlite3
from collections import defaultdict

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.database import (
    add_subject,
    delete_subject,
    list_subject_names,
    list_subjects,
    lock_subject,
    replace_subject_sessions,
    update_subject_location,
    update_subject_name,
    upsert_user,
)
from src.sigaa_schedule import parse_sigaa_schedule

SUBJECT_NAME, SUBJECT_SCHEDULE, SUBJECT_DAYS, SUBJECT_START, SUBJECT_END, SUBJECT_LOCATION = range(6)
REMOVE_SELECT, REMOVE_CONFIRM = range(10, 12)
LOCK_SELECT, LOCK_CONFIRM = range(20, 22)
EDIT_SELECT, EDIT_FIELD, EDIT_VALUE, EDIT_DAYS, EDIT_START, EDIT_END, EDIT_LOCATION = range(30, 37)

WEEKDAYS = {
    "seg": "segunda-feira", "segunda": "segunda-feira", "segunda-feira": "segunda-feira",
    "ter": "terça-feira", "terça": "terça-feira", "terca": "terça-feira", "terça-feira": "terça-feira", "terca-feira": "terça-feira",
    "qua": "quarta-feira", "quarta": "quarta-feira", "quarta-feira": "quarta-feira",
    "qui": "quinta-feira", "quinta": "quinta-feira", "quinta-feira": "quinta-feira",
    "sex": "sexta-feira", "sexta": "sexta-feira", "sexta-feira": "sexta-feira",
    "sab": "sábado", "sábado": "sábado", "sabado": "sábado",
}

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["📚 Minhas matérias", "⚙️ Gerenciar matérias"]],
    resize_keyboard=True,
)

MANAGE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["➕ Adicionar", "🗑️ Remover"],
        ["⏸️ Trancar", "✏️ Editar"],
        ["⬅️ Voltar"],
    ],
    resize_keyboard=True,
)

EDIT_FIELDS_KEYBOARD = ReplyKeyboardMarkup(
    [["📝 Nome", "🕐 Horário"], ["📍 Local"], ["❌ Cancelar"]],
    resize_keyboard=True,
)


def _valid_time(value: str) -> bool:
    if not re.fullmatch(r"\d{2}:\d{2}", value):
        return False
    hour, minute = map(int, value.split(":"))
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _parse_days(text: str) -> list[str]:
    normalized = text.lower().replace(";", ",")
    parsed: list[str] = []
    for raw_day in [item.strip() for item in normalized.split(",") if item.strip()]:
        day = WEEKDAYS.get(raw_day)
        if day and day not in parsed:
            parsed.append(day)
    return parsed


def _subject_keyboard(active_only: bool = True) -> ReplyKeyboardMarkup:
    names = list_subject_names(active_only=active_only)
    rows = [[name] for name in names]
    rows.append(["❌ Cancelar"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_user or not update.message:
        return
    user = update.effective_user
    upsert_user(update.effective_chat.id, user.id, user.first_name, user.username)
    await update.message.reply_text(
        "🕴️ Butler iniciado.\n\nSua grade está carregada e este chat foi registrado para os futuros lembretes automáticos.",
        reply_markup=MAIN_KEYBOARD,
    )


async def show_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    rows = list_subjects(include_locked=True)
    if not rows:
        await update.message.reply_text("Você ainda não possui matérias cadastradas.", reply_markup=MAIN_KEYBOARD)
        return

    grouped: dict[tuple[str, int], list] = defaultdict(list)
    for row in rows:
        grouped[(row["name"], row["active"])].append(row)

    parts = ["📚 *Matérias cadastradas*\n"]
    for (name, active), sessions in grouped.items():
        status = "" if active else " — ⏸️ TRANCADA"
        parts.append(f"*{name}*{status}")
        for session in sessions:
            if session["weekday"] is None:
                continue
            location = session["location"] or "Local não informado"
            parts.append(f"• {session['weekday'].capitalize()} — {session['start_time']}–{session['end_time']}\n  📍 {location}")
        parts.append("")

    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def manage_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "⚙️ *Gerenciar matérias*\n\nEscolha o que deseja fazer:",
            parse_mode="Markdown",
            reply_markup=MANAGE_KEYBOARD,
        )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Menu principal.", reply_markup=MAIN_KEYBOARD)


# -------------------- ADICIONAR --------------------
async def add_subject_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    context.user_data["new_subject"] = {}
    await update.message.reply_text("➕ Qual é o nome da disciplina?", reply_markup=ReplyKeyboardRemove())
    return SUBJECT_NAME


async def subject_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if len(name) < 2:
        await update.message.reply_text("Informe um nome válido.")
        return SUBJECT_NAME
    context.user_data["new_subject"]["name"] = name
    await update.message.reply_text(
        "Informe o *código de horário do SIGAA*.\nEx.: `3T23`, `35M45`, `24M23`.\n\nSe for um horário especial, digite `manual`.",
        parse_mode="Markdown",
    )
    return SUBJECT_SCHEDULE


async def subject_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if value.lower() == "manual":
        await update.message.reply_text("Em quais dias? Ex.: `seg, qua`.", parse_mode="Markdown")
        return SUBJECT_DAYS
    try:
        schedule = parse_sigaa_schedule(value)
    except ValueError:
        await update.message.reply_text("Código inválido. Tente `3T23`, `35M45` ou digite `manual`.", parse_mode="Markdown")
        return SUBJECT_SCHEDULE
    data = context.user_data["new_subject"]
    data.update(days=schedule.weekdays, start_time=schedule.start_time, end_time=schedule.end_time, sigaa_code=schedule.code)
    await update.message.reply_text(f"✅ {schedule.description}.\nQual é a sala/local?")
    return SUBJECT_LOCATION


async def subject_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    days = _parse_days(update.message.text or "")
    if not days:
        await update.message.reply_text("Não reconheci os dias. Ex.: `seg, qua`.", parse_mode="Markdown")
        return SUBJECT_DAYS
    context.user_data["new_subject"]["days"] = days
    await update.message.reply_text("Horário de início (`HH:MM`):", parse_mode="Markdown")
    return SUBJECT_START


async def subject_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if not _valid_time(value):
        await update.message.reply_text("Horário inválido. Use `HH:MM`.", parse_mode="Markdown")
        return SUBJECT_START
    context.user_data["new_subject"]["start_time"] = value
    await update.message.reply_text("Horário de término (`HH:MM`):", parse_mode="Markdown")
    return SUBJECT_END


async def subject_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if not _valid_time(value) or value <= context.user_data["new_subject"]["start_time"]:
        await update.message.reply_text("Término inválido. Ele precisa ser posterior ao início.")
        return SUBJECT_END
    context.user_data["new_subject"]["end_time"] = value
    await update.message.reply_text("Qual é a sala/local?")
    return SUBJECT_LOCATION


async def subject_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    location = (update.message.text or "").strip()
    data = context.user_data["new_subject"]
    sessions = [(day, data["start_time"], data["end_time"], location) for day in data["days"]]
    try:
        add_subject(data["name"], sessions)
    except sqlite3.IntegrityError:
        await update.message.reply_text("Já existe uma matéria com esse nome.", reply_markup=MANAGE_KEYBOARD)
        context.user_data.pop("new_subject", None)
        return ConversationHandler.END
    await update.message.reply_text(f"✅ *{data['name']}* cadastrada.", parse_mode="Markdown", reply_markup=MANAGE_KEYBOARD)
    context.user_data.pop("new_subject", None)
    return ConversationHandler.END


# -------------------- REMOVER --------------------
async def remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not list_subject_names(active_only=False):
        await update.message.reply_text("Não há matérias cadastradas.", reply_markup=MANAGE_KEYBOARD)
        return ConversationHandler.END
    await update.message.reply_text("🗑️ Qual matéria deseja remover definitivamente?", reply_markup=_subject_keyboard(False))
    return REMOVE_SELECT


async def remove_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if name == "❌ Cancelar":
        return await cancel_management(update, context)
    if name not in list_subject_names(active_only=False):
        await update.message.reply_text("Selecione uma matéria da lista.")
        return REMOVE_SELECT
    context.user_data["target_subject"] = name
    await update.message.reply_text(
        f"⚠️ Remover *{name}* apaga a matéria e todos os horários definitivamente. Confirmar?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["✅ Sim", "❌ Não"]], resize_keyboard=True),
    )
    return REMOVE_CONFIRM


async def remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if (update.message.text or "") == "✅ Sim":
        name = context.user_data.get("target_subject")
        delete_subject(name)
        await update.message.reply_text(f"🗑️ {name} removida.", reply_markup=MANAGE_KEYBOARD)
    else:
        await update.message.reply_text("Remoção cancelada.", reply_markup=MANAGE_KEYBOARD)
    context.user_data.pop("target_subject", None)
    return ConversationHandler.END


# -------------------- TRANCAR --------------------
async def lock_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not list_subject_names():
        await update.message.reply_text("Não há matérias ativas para trancar.", reply_markup=MANAGE_KEYBOARD)
        return ConversationHandler.END
    await update.message.reply_text("⏸️ Qual matéria deseja marcar como trancada/desistida?", reply_markup=_subject_keyboard(True))
    return LOCK_SELECT


async def lock_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if name == "❌ Cancelar":
        return await cancel_management(update, context)
    if name not in list_subject_names():
        await update.message.reply_text("Selecione uma matéria ativa da lista.")
        return LOCK_SELECT
    context.user_data["target_subject"] = name
    await update.message.reply_text(
        f"Trancar *{name}*? Ela continuará no histórico, mas deixará de participar da grade ativa e dos lembretes.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["✅ Sim", "❌ Não"]], resize_keyboard=True),
    )
    return LOCK_CONFIRM


async def lock_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if (update.message.text or "") == "✅ Sim":
        name = context.user_data.get("target_subject")
        lock_subject(name)
        await update.message.reply_text(f"⏸️ {name} foi marcada como trancada.", reply_markup=MANAGE_KEYBOARD)
    else:
        await update.message.reply_text("Operação cancelada.", reply_markup=MANAGE_KEYBOARD)
    context.user_data.pop("target_subject", None)
    return ConversationHandler.END


# -------------------- EDITAR --------------------
async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not list_subject_names():
        await update.message.reply_text("Não há matérias ativas para editar.", reply_markup=MANAGE_KEYBOARD)
        return ConversationHandler.END
    await update.message.reply_text("✏️ Qual matéria deseja editar?", reply_markup=_subject_keyboard(True))
    return EDIT_SELECT


async def edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if name == "❌ Cancelar":
        return await cancel_management(update, context)
    if name not in list_subject_names():
        await update.message.reply_text("Selecione uma matéria da lista.")
        return EDIT_SELECT
    context.user_data["edit_subject"] = name
    await update.message.reply_text(f"Editando *{name}*. O que deseja alterar?", parse_mode="Markdown", reply_markup=EDIT_FIELDS_KEYBOARD)
    return EDIT_FIELD


async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = (update.message.text or "").strip()
    if choice == "❌ Cancelar":
        return await cancel_management(update, context)
    context.user_data["edit_field"] = choice
    if choice == "📝 Nome":
        await update.message.reply_text("Digite o novo nome:", reply_markup=ReplyKeyboardRemove())
        return EDIT_VALUE
    if choice == "🕐 Horário":
        await update.message.reply_text("Digite o novo código SIGAA ou `manual` para informar dia e horário manualmente:", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
        return EDIT_VALUE
    if choice == "📍 Local":
        await update.message.reply_text("Digite o novo local/sala:", reply_markup=ReplyKeyboardRemove())
        return EDIT_LOCATION
    await update.message.reply_text("Escolha Nome, Horário ou Local.", reply_markup=EDIT_FIELDS_KEYBOARD)
    return EDIT_FIELD


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    name = context.user_data["edit_subject"]
    field = context.user_data["edit_field"]
    if field == "📝 Nome":
        try:
            update_subject_name(name, value)
        except sqlite3.IntegrityError:
            await update.message.reply_text("Já existe uma matéria com esse nome. Tente outro.")
            return EDIT_VALUE
        await update.message.reply_text("✅ Nome atualizado.", reply_markup=MANAGE_KEYBOARD)
        return ConversationHandler.END
    if value.lower() == "manual":
        await update.message.reply_text("Em quais dias? Ex.: `seg, qua`.", parse_mode="Markdown")
        return EDIT_DAYS
    try:
        schedule = parse_sigaa_schedule(value)
    except ValueError:
        await update.message.reply_text("Código inválido. Digite outro ou `manual`.", parse_mode="Markdown")
        return EDIT_VALUE
    context.user_data["edit_schedule"] = {
        "days": schedule.weekdays,
        "start": schedule.start_time,
        "end": schedule.end_time,
    }
    await update.message.reply_text(f"✅ {schedule.description}. Agora informe a sala/local para esse horário:")
    return EDIT_LOCATION


async def edit_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    days = _parse_days(update.message.text or "")
    if not days:
        await update.message.reply_text("Dias inválidos. Ex.: `seg, qua`.", parse_mode="Markdown")
        return EDIT_DAYS
    context.user_data["edit_schedule"] = {"days": days}
    await update.message.reply_text("Novo horário de início (`HH:MM`):", parse_mode="Markdown")
    return EDIT_START


async def edit_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if not _valid_time(value):
        await update.message.reply_text("Horário inválido.")
        return EDIT_START
    context.user_data["edit_schedule"]["start"] = value
    await update.message.reply_text("Novo horário de término (`HH:MM`):", parse_mode="Markdown")
    return EDIT_END


async def edit_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if not _valid_time(value) or value <= context.user_data["edit_schedule"]["start"]:
        await update.message.reply_text("Término inválido.")
        return EDIT_END
    context.user_data["edit_schedule"]["end"] = value
    await update.message.reply_text("Informe a sala/local para esse horário:")
    return EDIT_LOCATION


async def edit_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    location = (update.message.text or "").strip()
    name = context.user_data["edit_subject"]
    if context.user_data.get("edit_field") == "📍 Local":
        update_subject_location(name, location)
        await update.message.reply_text("✅ Local atualizado.", reply_markup=MANAGE_KEYBOARD)
        return ConversationHandler.END
    schedule = context.user_data["edit_schedule"]
    sessions = [(day, schedule["start"], schedule["end"], location) for day in schedule["days"]]
    replace_subject_sessions(name, sessions)
    await update.message.reply_text("✅ Horário atualizado.", reply_markup=MANAGE_KEYBOARD)
    return ConversationHandler.END


async def cancel_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    for key in ("target_subject", "edit_subject", "edit_field", "edit_schedule", "new_subject"):
        context.user_data.pop(key, None)
    if update.message:
        await update.message.reply_text("Operação cancelada.", reply_markup=MANAGE_KEYBOARD)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await cancel_management(update, context)


def register_handlers(application) -> None:
    add_conversation = ConversationHandler(
        entry_points=[CommandHandler("adicionar_materia", add_subject_start), MessageHandler(filters.Regex(r"^➕ Adicionar$"), add_subject_start)],
        states={
            SUBJECT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, subject_name)],
            SUBJECT_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, subject_schedule)],
            SUBJECT_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, subject_days)],
            SUBJECT_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, subject_start_time)],
            SUBJECT_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, subject_end_time)],
            SUBJECT_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, subject_location)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    remove_conversation = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🗑️ Remover$"), remove_start)],
        states={REMOVE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_select)], REMOVE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_confirm)]},
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    lock_conversation = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^⏸️ Trancar$"), lock_start)],
        states={LOCK_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, lock_select)], LOCK_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, lock_confirm)]},
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    edit_conversation = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^✏️ Editar$"), edit_start)],
        states={
            EDIT_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_select)],
            EDIT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field)],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)],
            EDIT_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_days)],
            EDIT_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_start_time)],
            EDIT_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_end_time)],
            EDIT_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_location)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("materias", show_subjects))
    application.add_handler(add_conversation)
    application.add_handler(remove_conversation)
    application.add_handler(lock_conversation)
    application.add_handler(edit_conversation)
    application.add_handler(MessageHandler(filters.Regex(r"^📚 Minhas matérias$"), show_subjects))
    application.add_handler(MessageHandler(filters.Regex(r"^⚙️ Gerenciar matérias$"), manage_subjects))
    application.add_handler(MessageHandler(filters.Regex(r"^⬅️ Voltar$"), back_to_main))
