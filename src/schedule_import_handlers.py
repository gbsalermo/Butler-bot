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
        "📥 Envie sua grade em *PDF com texto pesquisável* ou em arquivo `.txt`.\n\n"
        "Não aceito imagem, foto ou PDF escaneado nesta versão. Se você só tiver uma imagem, peça a qualquer IA/ferramenta para converter a grade em *PDF com texto pesquisável* e envie o resultado aqui.\n\n"
        "Se preferir, também dá para cadastrar as matérias uma por uma em *⚙️ Gerenciar matérias*.\n\n"
        "Quando eu ler o arquivo, mostro uma prévia antes de salvar.",
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

    if message.photo:
        await message.reply_text(
            "Essa grade veio como imagem. Para manter o Butler simples e compatível com a hospedagem, eu não faço OCR aqui.\n\n"
            "Peça a uma IA/ferramenta para converter a imagem em *PDF com texto pesquisável* e me envie esse PDF, ou cadastre as matérias manualmente.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE

    if not message.document:
        await message.reply_text(
            "Estou esperando um *PDF com texto pesquisável* ou um arquivo `.txt`.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE

    name = (message.document.file_name or "grade").lower()
    mime = (message.document.mime_type or "").lower()

    if mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        await message.reply_text(
            "Imagem não entra direto, chefe. Converta primeiro para *PDF com texto pesquisável* usando uma IA/ferramenta e me mande o PDF.\n\n"
            "Ou, se quiser sofrer do jeito tradicional, cadastre matéria por matéria em *⚙️ Gerenciar matérias*.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE

    if mime == "application/pdf" or name.endswith(".pdf"):
        suffix = ".pdf"
    elif mime.startswith("text/") or name.endswith(".txt"):
        suffix = ".txt"
    else:
        await message.reply_text(
            "Formato não aceito. Use *PDF com texto pesquisável* ou `.txt`.\n\n"
            "Se sua grade estiver numa imagem, converta antes para PDF com texto.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE

    file_obj = await message.document.get_file()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        path = Path(tmp.name)

    try:
        await file_obj.download_to_drive(custom_path=str(path))
        text = extract_text_from_file(path)
        subjects = parse_schedule_text(text)
    except Exception as exc:
        await message.reply_text(
            "Não consegui ler essa grade como texto.\n\n"
            f"`{type(exc).__name__}: {exc}`\n\n"
            "Se esse PDF veio de uma imagem/scan, converta-o para *PDF com texto pesquisável* e tente novamente.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE
    finally:
        path.unlink(missing_ok=True)

    if not subjects:
        await message.reply_text(
            "Eu consegui extrair texto do arquivo, mas não encontrei códigos SIGAA como `35M45`, `24M23` ou `3T23`.\n\n"
            "Confira se a conversão preservou nome da matéria, local e código de horário. Se não, você ainda pode cadastrar manualmente.",
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
        "Confere antes de importar. PDF com texto é mais confiável que OCR, mas ainda não vou sair alterando sua vida acadêmica sem autorização.",
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
        f"✅ Grade importada: {len(subjects)} matéria(s).\n\nDigitar tudo uma por uma continua disponível, mas felizmente não foi necessário.",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


def register_schedule_import(application) -> None:
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📥 Importar grade por PDF/texto$"), import_start)],
        states={
            WAIT_FILE: [MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, receive_file)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_import)],
        },
        fallbacks=[CommandHandler("cancelar", confirm_import)],
    )
    application.add_handler(conv, group=-15)
