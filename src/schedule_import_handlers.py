import tempfile
from pathlib import Path

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.database import upsert_subject_schedule
from src.schedule_importer import ImportedSubject, extract_text_from_file, parse_schedule_text
from src.ui_layout import MAIN_KEYBOARD

WAIT_FILE, CONFIRM = range(720, 722)
WAIT_KEYBOARD = ReplyKeyboardMarkup([["❌ Cancelar ação"]], resize_keyboard=True)
CONFIRM_KEYBOARD = ReplyKeyboardMarkup([["✅ Importar grade", "❌ Cancelar ação"]], resize_keyboard=True)


async def import_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Manda o PDF ou uma imagem da sua grade do SIGAA.\n\nEu vou tentar identificar matéria, local e código de horário e *vou te mostrar uma prévia antes de salvar*. Nada de confiar cegamente em OCR — já temos problemas suficientes.",
        parse_mode="Markdown",
        reply_markup=WAIT_KEYBOARD,
    )
    return WAIT_FILE


async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if not message:
        return WAIT_FILE

    if (message.text or "") == "❌ Cancelar ação":
        await message.reply_text("Importação cancelada. Nenhuma matéria foi alterada.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    file_obj = None
    suffix = ".jpg"
    if message.photo:
        file_obj = await message.photo[-1].get_file()
        suffix = ".jpg"
    elif message.document:
        name = (message.document.file_name or "grade").lower()
        mime = message.document.mime_type or ""
        if mime == "application/pdf" or name.endswith(".pdf"):
            suffix = ".pdf"
        elif mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            suffix = Path(name).suffix or ".jpg"
        else:
            await message.reply_text("Use um PDF ou imagem (JPG/PNG/WebP).", reply_markup=WAIT_KEYBOARD)
            return WAIT_FILE
        file_obj = await message.document.get_file()
    else:
        await message.reply_text("Estou esperando um PDF ou uma imagem da grade.", reply_markup=WAIT_KEYBOARD)
        return WAIT_FILE

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        path = Path(tmp.name)
    try:
        await file_obj.download_to_drive(custom_path=str(path))
        text = extract_text_from_file(path)
        subjects = parse_schedule_text(text)
    except Exception as exc:
        await message.reply_text(
            f"Não consegui ler essa grade.\n\n`{type(exc).__name__}: {exc}`\n\nSe for imagem/PDF escaneado, confira se o Tesseract OCR está instalado.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE
    finally:
        path.unlink(missing_ok=True)

    if not subjects:
        await message.reply_text(
            "Eu li o arquivo, mas não encontrei linhas com códigos SIGAA do tipo `35M45` ou `3T23`. Tente uma imagem mais nítida ou um PDF original.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE

    context.user_data["schedule_import"] = subjects
    lines = ["📚 *Prévia da grade que eu entendi*", ""]
    for subject in subjects:
        lines.append(f"• *{subject.name}* — `{subject.code}`")
        for day, start, end, location in subject.sessions:
            lines.append(f"   {day.capitalize()} • {start}–{end} • {location or 'local não identificado'}")
    lines.extend([
        "",
        "Confere antes de importar. Se o SIGAA estiver errado ou o OCR tiver viajado, cancele e ajuste manualmente depois.",
    ])
    await message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=CONFIRM_KEYBOARD)
    return CONFIRM


async def confirm_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text != "✅ Importar grade":
        context.user_data.pop("schedule_import", None)
        await update.message.reply_text("Beleza. Não alterei sua grade.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    subjects: list[ImportedSubject] = context.user_data.pop("schedule_import", [])
    for subject in subjects:
        upsert_subject_schedule(subject.name, subject.sessions)

    await update.message.reply_text(
        f"✅ Grade importada: {len(subjects)} matéria(s).\n\nAgora sim. Digitar matéria por matéria em 2026 seria uma derrota administrativa.",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


def register_schedule_import(application) -> None:
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📥 Importar grade por PDF/imagem$"), import_start)],
        states={
            WAIT_FILE: [
                MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, receive_file),
            ],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_import)],
        },
        fallbacks=[CommandHandler("cancelar", confirm_import)],
    )
    application.add_handler(conv, group=-15)
