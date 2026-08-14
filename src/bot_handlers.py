import re
import sqlite3
from collections import defaultdict

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.database import add_subject, list_subjects, upsert_user
from src.sigaa_schedule import parse_sigaa_schedule

SUBJECT_NAME, SUBJECT_SCHEDULE, SUBJECT_DAYS, SUBJECT_START, SUBJECT_END, SUBJECT_LOCATION = range(6)

WEEKDAYS = {
    "seg": "segunda-feira",
    "segunda": "segunda-feira",
    "segunda-feira": "segunda-feira",
    "ter": "terça-feira",
    "terça": "terça-feira",
    "terca": "terça-feira",
    "terça-feira": "terça-feira",
    "terca-feira": "terça-feira",
    "qua": "quarta-feira",
    "quarta": "quarta-feira",
    "quarta-feira": "quarta-feira",
    "qui": "quinta-feira",
    "quinta": "quinta-feira",
    "quinta-feira": "quinta-feira",
    "sex": "sexta-feira",
    "sexta": "sexta-feira",
    "sexta-feira": "sexta-feira",
    "sab": "sábado",
    "sábado": "sábado",
    "sabado": "sábado",
}

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["📚 Minhas matérias", "⚙️ Gerenciar matérias"]],
    resize_keyboard=True,
)

MANAGE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📚 Ver matérias", "➕ Adicionar matéria"],
        ["⬅️ Voltar"],
    ],
    resize_keyboard=True,
)


def _valid_time(value: str) -> bool:
    if not re.fullmatch(r"\d{2}:\d{2}", value):
        return False
    hour, minute = map(int, value.split(":"))
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _parse_days(text: str) -> list[str]:
    normalized = text.lower().replace(";", ",")
    raw_days = [item.strip() for item in normalized.split(",") if item.strip()]
    parsed: list[str] = []
    for raw_day in raw_days:
        day = WEEKDAYS.get(raw_day)
        if day and day not in parsed:
            parsed.append(day)
    return parsed


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_user or not update.message:
        return

    user = update.effective_user
    upsert_user(
        chat_id=update.effective_chat.id,
        user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )

    await update.message.reply_text(
        "🕴️ Butler iniciado.\n\n"
        "Seu chat foi registrado para que eu possa enviar lembretes e avisos automaticamente nas próximas etapas.\n\n"
        "Sua grade atual já está cadastrada. Use os botões abaixo para consultar ou gerenciar suas matérias.",
        reply_markup=MAIN_KEYBOARD,
    )


async def show_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    rows = list_subjects()
    if not rows:
        await update.message.reply_text("Você ainda não possui matérias cadastradas.", reply_markup=MAIN_KEYBOARD)
        return

    grouped: dict[str, list] = defaultdict(list)
    for row in rows:
        grouped[row["name"]].append(row)

    parts = ["📚 *Matérias cadastradas*\n"]
    for name, sessions in grouped.items():
        parts.append(f"*{name}*")
        for session in sessions:
            location = session["location"] or "Local não informado"
            parts.append(
                f"• {session['weekday'].capitalize()} — {session['start_time']}–{session['end_time']}\n"
                f"  📍 {location}"
            )
        parts.append("")

    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def manage_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "⚙️ *Gerenciar matérias*\n\n"
        "Aqui você pode consultar sua grade ou cadastrar uma nova disciplina.",
        parse_mode="Markdown",
        reply_markup=MANAGE_KEYBOARD,
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Menu principal.", reply_markup=MAIN_KEYBOARD)


async def add_subject_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    context.user_data["new_subject"] = {}
    await update.message.reply_text(
        "➕ Vamos cadastrar uma matéria.\n\nQual é o nome da disciplina?\n\nDigite /cancelar para sair.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return SUBJECT_NAME


async def subject_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if len(name) < 2:
        await update.message.reply_text("Informe um nome válido para a matéria.")
        return SUBJECT_NAME

    context.user_data["new_subject"]["name"] = name
    await update.message.reply_text(
        "Informe o *código de horário do SIGAA*.\n\n"
        "Exemplos:\n"
        "• `3T23` → terça à tarde, aproximadamente das 14h às 16h\n"
        "• `35M45` → terça e quinta de manhã, aproximadamente das 10h às 12h\n"
        "• `24M23` → segunda e quarta de manhã, aproximadamente das 8h às 10h\n\n"
        "Se o horário não seguir o padrão do SIGAA, digite `manual`.",
        parse_mode="Markdown",
    )
    return SUBJECT_SCHEDULE


async def subject_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()

    if value.lower() == "manual":
        context.user_data["new_subject"]["schedule_mode"] = "manual"
        await update.message.reply_text(
            "Em quais dias ela acontece?\n\n"
            "Exemplos: `seg, qua` ou `terça, quinta`.",
            parse_mode="Markdown",
        )
        return SUBJECT_DAYS

    try:
        schedule = parse_sigaa_schedule(value)
    except ValueError:
        await update.message.reply_text(
            "Não reconheci esse código. Use algo como `3T23`, `35M45` ou `24M23`.\n"
            "Se for um horário especial, digite `manual`.",
            parse_mode="Markdown",
        )
        return SUBJECT_SCHEDULE

    data = context.user_data["new_subject"]
    data["schedule_mode"] = "sigaa"
    data["sigaa_code"] = schedule.code
    data["days"] = schedule.weekdays
    data["start_time"] = schedule.start_time
    data["end_time"] = schedule.end_time

    await update.message.reply_text(
        f"✅ Horário traduzido: *{schedule.description}*.\n\n"
        f"Horário exato usado pelo Butler: `{schedule.start_time}–{schedule.end_time}`.\n\n"
        "Qual é a sala/local da aula?",
        parse_mode="Markdown",
    )
    return SUBJECT_LOCATION


async def subject_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    days = _parse_days(update.message.text or "")
    if not days:
        await update.message.reply_text("Não reconheci os dias. Tente, por exemplo: `seg, qua`.", parse_mode="Markdown")
        return SUBJECT_DAYS
    context.user_data["new_subject"]["days"] = days
    await update.message.reply_text("Qual o horário de início? Use `HH:MM`, por exemplo `14:00`.", parse_mode="Markdown")
    return SUBJECT_START


async def subject_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if not _valid_time(value):
        await update.message.reply_text("Horário inválido. Use `HH:MM`, por exemplo `08:00`.", parse_mode="Markdown")
        return SUBJECT_START
    context.user_data["new_subject"]["start_time"] = value
    await update.message.reply_text("E qual o horário de término? Use `HH:MM`.", parse_mode="Markdown")
    return SUBJECT_END


async def subject_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if not _valid_time(value):
        await update.message.reply_text("Horário inválido. Use `HH:MM`.", parse_mode="Markdown")
        return SUBJECT_END

    start_time = context.user_data["new_subject"]["start_time"]
    if value <= start_time:
        await update.message.reply_text("O término precisa ser posterior ao início. Informe novamente.")
        return SUBJECT_END

    context.user_data["new_subject"]["end_time"] = value
    await update.message.reply_text("Qual é a sala/local da aula?")
    return SUBJECT_LOCATION


async def subject_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    location = (update.message.text or "").strip()
    data = context.user_data["new_subject"]
    sessions = [(day, data["start_time"], data["end_time"], location) for day in data["days"]]

    try:
        add_subject(data["name"], sessions)
    except sqlite3.IntegrityError:
        await update.message.reply_text(
            "Já existe uma matéria com esse nome. O cadastro foi cancelado para evitar duplicidade.",
            reply_markup=MAIN_KEYBOARD,
        )
        context.user_data.pop("new_subject", None)
        return ConversationHandler.END

    code_text = f"\nCódigo SIGAA: `{data['sigaa_code']}`" if data.get("sigaa_code") else ""
    await update.message.reply_text(
        f"✅ *{data['name']}* cadastrada com sucesso.{code_text}",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    context.user_data.pop("new_subject", None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("new_subject", None)
    if update.message:
        await update.message.reply_text("Cadastro cancelado.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


def register_handlers(application) -> None:
    add_subject_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("adicionar_materia", add_subject_start),
            MessageHandler(filters.Regex(r"^➕ Adicionar matéria$"), add_subject_start),
        ],
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

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("materias", show_subjects))
    application.add_handler(add_subject_conversation)
    application.add_handler(MessageHandler(filters.Regex(r"^📚 Minhas matérias$"), show_subjects))
    application.add_handler(MessageHandler(filters.Regex(r"^📚 Ver matérias$"), show_subjects))
    application.add_handler(MessageHandler(filters.Regex(r"^⚙️ Gerenciar matérias$"), manage_subjects))
    application.add_handler(MessageHandler(filters.Regex(r"^⬅️ Voltar$"), back_to_main))
