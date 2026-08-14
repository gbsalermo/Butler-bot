import tempfile
from collections import defaultdict
from pathlib import Path

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.workout_importer import ImportedWorkoutExercise, parse_workout_file
from src.workout_import_store import replace_workout_plan

WAIT_FILE, CONFIRM = range(860, 862)
WAIT_KEYBOARD = ReplyKeyboardMarkup([["❌ Cancelar ação"]], resize_keyboard=True)
GENERIC_WORKOUT_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📥 Importar treino por PDF/texto"],
        ["➕ Adicionar exercício", "📋 Ver rotina"],
        ["⬅️ Voltar ao cotidiano"],
    ],
    resize_keyboard=True,
)
CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    [["✅ Importar treino", "❌ Cancelar ação"]],
    resize_keyboard=True,
)


async def generic_workout_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🏋️ *Musculação*\n\n"
        "Você pode cadastrar exercício por exercício ou importar uma ficha inteira por PDF textual/`.txt`. "
        "Assim ninguém precisa transformar o treino em prova de resistência antes mesmo de entrar na academia.",
        parse_mode="Markdown",
        reply_markup=GENERIC_WORKOUT_KEYBOARD,
    )


async def import_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📥 Envie seu treino em *PDF com texto pesquisável* ou `.txt`.\n\n"
        "Eu não faço OCR: foto, print e PDF escaneado precisam ser convertidos antes para PDF com texto pesquisável ou texto puro.\n\n"
        "Formato recomendado, mas não precisa ser exatamente igual:\n\n"
        "`SEGUNDA — Peito`\n"
        "`Supino reto | 4x8-10 | 40 kg`\n"
        "`Crucifixo | 3x12 | 12 kg`\n\n"
        "Também aceito `;` no lugar de `|` e linhas como `Supino reto 4x8-10 40 kg`. "
        "Eu mostro uma prévia antes de substituir a rotina atual.",
        parse_mode="Markdown",
        reply_markup=WAIT_KEYBOARD,
    )
    return WAIT_FILE


async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if not message:
        return WAIT_FILE

    if (message.text or "") == "❌ Cancelar ação":
        await message.reply_text("Importação cancelada. Sua rotina continua como estava.", reply_markup=GENERIC_WORKOUT_KEYBOARD)
        return ConversationHandler.END

    if message.photo:
        await message.reply_text(
            "Isso veio como imagem. Para manter o Butler simples e compatível com a hospedagem, converta antes para *PDF com texto pesquisável* ou `.txt`.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE

    if not message.document:
        await message.reply_text("Estou esperando um PDF textual ou `.txt`.", reply_markup=WAIT_KEYBOARD)
        return WAIT_FILE

    name = (message.document.file_name or "treino").lower()
    mime = (message.document.mime_type or "").lower()
    if mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        await message.reply_text(
            "Imagem não entra direto. Converta para *PDF com texto pesquisável* ou `.txt` e tente de novo.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE

    if mime == "application/pdf" or name.endswith(".pdf"):
        suffix = ".pdf"
    elif mime.startswith("text/") or name.endswith(".txt"):
        suffix = ".txt"
    else:
        await message.reply_text("Formato não aceito. Use PDF textual ou `.txt`.", reply_markup=WAIT_KEYBOARD)
        return WAIT_FILE

    telegram_file = await message.document.get_file()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        path = Path(tmp.name)

    try:
        await telegram_file.download_to_drive(custom_path=str(path))
        exercises = parse_workout_file(path)
    except Exception as exc:
        await message.reply_text(
            "Não consegui interpretar esse arquivo como uma ficha de treino textual.\n\n"
            f"`{type(exc).__name__}: {exc}`\n\n"
            "Se ele veio de imagem/scan, converta antes. Se já for texto, confira se cada exercício informa séries e repetições, por exemplo `4x8-10`.",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE
    finally:
        path.unlink(missing_ok=True)

    if not exercises:
        await message.reply_text(
            "Consegui ler o texto, mas não encontrei exercícios com *dia + séries x repetições*.\n\n"
            "Use algo como:\n`SEGUNDA — Peito`\n`Supino reto | 4x8-10 | 40 kg`",
            parse_mode="Markdown",
            reply_markup=WAIT_KEYBOARD,
        )
        return WAIT_FILE

    context.user_data["workout_import"] = exercises
    grouped: dict[tuple[str, str], list[ImportedWorkoutExercise]] = defaultdict(list)
    for exercise in exercises:
        grouped[(exercise.weekday, exercise.focus)].append(exercise)

    lines = ["🏋️ *Prévia do treino que eu entendi*", ""]
    for (weekday, focus), rows in grouped.items():
        lines.append(f"*{weekday.capitalize()} — {focus}*")
        for exercise in rows:
            scheme = f"{exercise.sets}x{exercise.reps}" if exercise.sets else (exercise.reps or "")
            load = f" — {exercise.load}" if exercise.load else ""
            lines.append(f"• {exercise.name} — {scheme}{load}")
        lines.append("")

    lines.extend([
        f"Total: *{len(exercises)} exercício(s)*.",
        "",
        "⚠️ Ao confirmar, esta ficha *substitui a rotina manual atual*. Histórico de tarefas, finanças e outros módulos não é afetado.",
        "",
        "Confere primeiro. Eu gosto de automatizar trabalho chato; inventar leg day alheio não está entre minhas atribuições.",
    ])
    await message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=CONFIRM_KEYBOARD)
    return CONFIRM


async def confirm_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text != "✅ Importar treino":
        context.user_data.pop("workout_import", None)
        await update.message.reply_text("Certo. Não mexi na sua rotina.", reply_markup=GENERIC_WORKOUT_KEYBOARD)
        return ConversationHandler.END

    exercises: list[ImportedWorkoutExercise] = context.user_data.pop("workout_import", [])
    if not exercises:
        await update.message.reply_text("A prévia expirou ou ficou vazia. Envie o arquivo novamente.", reply_markup=GENERIC_WORKOUT_KEYBOARD)
        return ConversationHandler.END

    replace_workout_plan(exercises)
    days = len({exercise.weekday for exercise in exercises})
    await update.message.reply_text(
        f"✅ Treino importado: *{days} dia(s)* e *{len(exercises)} exercício(s)*.\n\n"
        "Pronto. Você economizou a parte menos atlética da academia: digitar ficha.",
        parse_mode="Markdown",
        reply_markup=GENERIC_WORKOUT_KEYBOARD,
    )
    return ConversationHandler.END


def register_workout_import(application) -> None:
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📥 Importar treino por PDF/texto$"), import_start)],
        states={
            WAIT_FILE: [MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, receive_file)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_import)],
        },
        fallbacks=[CommandHandler("cancelar", confirm_import)],
    )
    application.add_handler(conv, group=-16)
    application.add_handler(MessageHandler(filters.Regex(r"^🏋️ Musculação$"), generic_workout_menu), group=-4)
