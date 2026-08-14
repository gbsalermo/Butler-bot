from collections import defaultdict

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

from src.database import list_subjects

ACADEMIC_KEYBOARD = ReplyKeyboardMarkup(
    [["📚 Minhas matérias", "⚙️ Gerenciar matérias"], ["🏠 Menu principal"]],
    resize_keyboard=True,
)


async def show_subjects_with_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    rows = list_subjects(include_locked=True)
    if not rows:
        await update.message.reply_text(
            "Você ainda não possui matérias cadastradas.",
            reply_markup=ACADEMIC_KEYBOARD,
        )
        raise ApplicationHandlerStop

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
            parts.append(
                f"• {session['weekday'].capitalize()} — "
                f"{session['start_time']}–{session['end_time']}\n"
                f"  📍 {location}"
            )
        parts.append("")

    await update.message.reply_text(
        "\n".join(parts),
        parse_mode="Markdown",
        reply_markup=ACADEMIC_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def back_to_academic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "📚 Área acadêmica. O que você precisa?",
            reply_markup=ACADEMIC_KEYBOARD,
        )
    raise ApplicationHandlerStop


def register_academic_navigation(application) -> None:
    application.add_handler(
        MessageHandler(filters.Regex(r"^📚 Minhas matérias$"), show_subjects_with_navigation),
        group=-2,
    )
    application.add_handler(
        MessageHandler(filters.Regex(r"^⬅️ Voltar$"), back_to_academic),
        group=-2,
    )
