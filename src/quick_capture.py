from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.config import BUTLER_TIMEZONE
from src.daily_store import add_item
from src.home_store import add_grocery_item
import src.lifestyle_handlers as lifestyle
from src.ui_layout import COTIDIANO_KEYBOARD

Q_TITLE, Q_WHEN, Q_DATE, Q_TIME = range(810, 814)
GROCERY_QUICK = 820

CANCEL = "❌ Cancelar ação"
WHEN_KEYBOARD = ReplyKeyboardMarkup(
    [["📍 Hoje", "📆 Outro dia"], ["🗂️ Sem data"], [CANCEL]],
    resize_keyboard=True,
)
CANCEL_KEYBOARD = ReplyKeyboardMarkup([[CANCEL]], resize_keyboard=True)


def _now() -> datetime:
    return datetime.now(ZoneInfo(BUTLER_TIMEZONE))


def _kind(text: str) -> str:
    lowered = text.lower()
    if "compromisso" in lowered:
        return "compromisso"
    if "pendência" in lowered or "pendencia" in lowered:
        return "pendencia"
    return "tarefa"


def _parse_date(value: str):
    v = value.strip().lower()
    if v in {"amanhã", "amanha"}:
        parsed = _now().date() + timedelta(days=1)
    else:
        try:
            parsed = datetime.strptime(value.strip(), "%d/%m/%Y").date()
        except ValueError:
            return False
    if parsed < _now().date():
        return "past"
    return parsed.isoformat()


def _parse_time(value: str):
    try:
        return datetime.strptime(value.strip(), "%H:%M").strftime("%H:%M")
    except ValueError:
        return False


def _future_datetime(due_date: str, due_time: str) -> bool:
    tz = ZoneInfo(BUTLER_TIMEZONE)
    scheduled = datetime.fromisoformat(f"{due_date}T{due_time}").replace(tzinfo=tz)
    return scheduled > _now()


async def quick_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    kind = _kind(update.message.text or "")
    context.user_data["quick_item"] = {"kind": kind}
    labels = {"tarefa": "tarefa", "compromisso": "compromisso", "pendencia": "pendência"}
    await update.message.reply_text(
        f"Qual é a {labels[kind]}? Manda só o essencial.",
        reply_markup=CANCEL_KEYBOARD,
    )
    return Q_TITLE


async def quick_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == CANCEL:
        return await quick_cancel(update, context)
    if len(text) < 2:
        await update.message.reply_text("Preciso de um título válido.", reply_markup=CANCEL_KEYBOARD)
        return Q_TITLE
    context.user_data["quick_item"]["title"] = text
    await update.message.reply_text("É para quando?", reply_markup=WHEN_KEYBOARD)
    return Q_WHEN


async def quick_when(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == CANCEL:
        return await quick_cancel(update, context)
    if text == "🗂️ Sem data":
        return await _save_quick(update, context, None, None)
    if text == "📍 Hoje":
        context.user_data["quick_item"]["due_date"] = _now().date().isoformat()
        await update.message.reply_text(
            "Qual horário? Use `HH:MM`. Não vale viajar no tempo, então horário passado eu recuso.",
            parse_mode="Markdown",
            reply_markup=CANCEL_KEYBOARD,
        )
        return Q_TIME
    if text == "📆 Outro dia":
        await update.message.reply_text(
            "Qual data? Use `DD/MM/AAAA` ou `amanhã`.",
            parse_mode="Markdown",
            reply_markup=CANCEL_KEYBOARD,
        )
        return Q_DATE
    await update.message.reply_text("Escolha Hoje, Outro dia, Sem data ou cancele.", reply_markup=WHEN_KEYBOARD)
    return Q_WHEN


async def quick_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == CANCEL:
        return await quick_cancel(update, context)
    parsed = _parse_date(text)
    if parsed is False:
        await update.message.reply_text("Data inválida. Use `DD/MM/AAAA` ou `amanhã`.", parse_mode="Markdown")
        return Q_DATE
    if parsed == "past":
        await update.message.reply_text("Essa data já passou, chefe. Escolha hoje ou uma data futura.")
        return Q_DATE
    context.user_data["quick_item"]["due_date"] = parsed
    await update.message.reply_text("Qual horário? Use `HH:MM`.", parse_mode="Markdown", reply_markup=CANCEL_KEYBOARD)
    return Q_TIME


async def quick_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == CANCEL:
        return await quick_cancel(update, context)
    parsed = _parse_time(text)
    if parsed is False:
        await update.message.reply_text("Horário inválido. Use `HH:MM`.", parse_mode="Markdown")
        return Q_TIME
    data = context.user_data["quick_item"]
    due_date = data["due_date"]
    if not _future_datetime(due_date, parsed):
        await update.message.reply_text(
            "Esse horário já passou. Eu organizo sua agenda, não reescrevo a linha do tempo. Escolha um horário futuro."
        )
        return Q_TIME
    return await _save_quick(update, context, due_date, parsed)


async def _save_quick(update: Update, context: ContextTypes.DEFAULT_TYPE, due_date: str | None, due_time: str | None) -> int:
    data = context.user_data.pop("quick_item")
    add_item(
        data["kind"],
        data["title"],
        due_date,
        due_time,
        details=None,
        reminder_minutes=0,
    )
    when = ""
    if due_date:
        friendly = datetime.fromisoformat(due_date).strftime("%d/%m/%Y")
        when = f" — {friendly}"
    if due_time:
        when += f" às {due_time}"
    await update.message.reply_text(
        f"✅ Salvo: {data['title']}{when}." if when else f"✅ Salvo: {data['title']}.",
        reply_markup=lifestyle._menu(data["kind"]),
    )
    return ConversationHandler.END


async def quick_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("quick_item", None)
    context.user_data.pop("quick_grocery", None)
    kind = (data or {}).get("kind")
    await update.message.reply_text(
        "Cancelei. Menos burocracia, pelo menos.",
        reply_markup=lifestyle._menu(kind) if kind else COTIDIANO_KEYBOARD,
    )
    return ConversationHandler.END


async def grocery_quick_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "O que está faltando?\n\nPode mandar só `sal`. Se quiser quantidade, use `café | 2 pacotes`.",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return GROCERY_QUICK


async def grocery_quick_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == CANCEL:
        return await quick_cancel(update, context)
    if len(text) < 2:
        await update.message.reply_text("Me diga o que está faltando.", reply_markup=CANCEL_KEYBOARD)
        return GROCERY_QUICK

    parts = [part.strip() for part in text.split("|", 1)]
    name = parts[0]
    quantity = parts[1] if len(parts) == 2 and parts[1] else None
    add_grocery_item(name, quantity, None)
    extra = f" ({quantity})" if quantity else ""
    await update.message.reply_text(
        f"🛒 Anotado: {name}{extra}. Quando estiver no mercado, eu lembro.",
        reply_markup=COTIDIANO_KEYBOARD,
    )
    return ConversationHandler.END


def register_quick_capture(application) -> None:
    # Mesmo group dos handlers antigos, mas registrado antes deles. Assim os fluxos
    # rápidos assumem as entradas e o restante (listar/editar/remover) continua intacto.
    daily_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ (Nova tarefa|Novo compromisso|Nova pendência)$"), quick_add_start)],
        states={
            Q_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, quick_title)],
            Q_WHEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, quick_when)],
            Q_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, quick_date)],
            Q_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, quick_time)],
        },
        fallbacks=[CommandHandler("cancelar", quick_cancel)],
    )
    grocery_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ Item faltando$"), grocery_quick_start)],
        states={GROCERY_QUICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, grocery_quick_save)]},
        fallbacks=[CommandHandler("cancelar", quick_cancel)],
    )
    application.add_handler(daily_conv, group=-1)
    application.add_handler(grocery_conv, group=-1)
