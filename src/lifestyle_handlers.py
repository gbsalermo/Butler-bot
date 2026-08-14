from datetime import date, datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.daily_store import add_item, complete_item, delete_item, get_item, list_items, snooze_item, update_item

ITEM_TITLE, ITEM_DATE, ITEM_TIME, ITEM_REMINDER, ITEM_DETAILS = range(100, 105)
COMPLETE_ID = 110
EDIT_ID, EDIT_FIELD, EDIT_VALUE = range(120, 123)
DELETE_ID, DELETE_CONFIRM = range(130, 132)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["🌙 Day-off"], ["📚 Matérias", "✅ Tarefas"], ["📅 Compromissos", "📌 Pendências"],
     ["🏠 Cotidiano", "🗓️ Hoje"], ["💰 Finanças"]], resize_keyboard=True
)

LABELS = {
    "tarefa": ("✅", "Tarefa", "Tarefas", "Nova tarefa", "Concluir tarefa", "Editar tarefa", "Remover tarefa"),
    "compromisso": ("📅", "Compromisso", "Compromissos", "Novo compromisso", "Concluir compromisso", "Editar compromisso", "Remover compromisso"),
    "pendencia": ("📌", "Pendência", "Pendências", "Nova pendência", "Resolver pendência", "Editar pendência", "Remover pendência"),
}


def _kind_from_text(text: str) -> str | None:
    t = text.lower()
    if "tarefa" in t: return "tarefa"
    if "compromisso" in t: return "compromisso"
    if "pendência" in t or "pendencia" in t: return "pendencia"
    return None


def _menu(kind: str) -> ReplyKeyboardMarkup:
    _, _, plural, add_label, complete_label, edit_label, remove_label = LABELS[kind]
    return ReplyKeyboardMarkup(
        [[f"➕ {add_label}", f"📋 Ver {plural.lower()}"],
         [f"☑️ {complete_label}", f"✏️ {edit_label}"],
         [f"🗑️ {remove_label}", "🏠 Menu principal"]], resize_keyboard=True
    )


def _parse_date(value: str):
    v = value.strip().lower()
    if v in {"sem data", "-", "nenhuma"}: return None
    if v == "hoje": return date.today().isoformat()
    if v in {"amanhã", "amanha"}: return (date.today() + timedelta(days=1)).isoformat()
    try: return datetime.strptime(value.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError: return False


def _parse_time(value: str):
    v = value.strip().lower()
    if v in {"sem horário", "sem horario", "-", "nenhum"}: return None
    try: return datetime.strptime(value.strip(), "%H:%M").strftime("%H:%M")
    except ValueError: return False


async def open_kind_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kind = _kind_from_text(update.message.text or "")
    if not kind: return
    icon, _, plural, *_ = LABELS[kind]
    await update.message.reply_text(f"{icon} *{plural}*\n\nO que você quer fazer?", parse_mode="Markdown", reply_markup=_menu(kind))


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    kind = _kind_from_text(update.message.text or "")
    context.user_data["new_daily_item"] = {"kind": kind}
    await update.message.reply_text("Qual é o título?", reply_markup=ReplyKeyboardRemove())
    return ITEM_TITLE


async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if len(text) < 2:
        await update.message.reply_text("Informe um título válido."); return ITEM_TITLE
    context.user_data["new_daily_item"]["title"] = text
    await update.message.reply_text("Para qual data? `DD/MM/AAAA`, `hoje`, `amanhã` ou `sem data`.", parse_mode="Markdown")
    return ITEM_DATE


async def add_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = _parse_date(update.message.text or "")
    if value is False:
        await update.message.reply_text("Data inválida."); return ITEM_DATE
    context.user_data["new_daily_item"]["due_date"] = value
    await update.message.reply_text("Qual o horário? `HH:MM` ou `sem horário`.", parse_mode="Markdown")
    return ITEM_TIME


async def add_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = _parse_time(update.message.text or "")
    if value is False:
        await update.message.reply_text("Horário inválido."); return ITEM_TIME
    context.user_data["new_daily_item"]["due_time"] = value
    if value:
        await update.message.reply_text("Quanto tempo antes devo avisar? Ex.: `5`, `10`, `30` minutos ou `0` para avisar na hora.", parse_mode="Markdown")
        return ITEM_REMINDER
    context.user_data["new_daily_item"]["reminder_minutes"] = 10
    await update.message.reply_text("Alguma observação? `-` se não houver.", parse_mode="Markdown")
    return ITEM_DETAILS


async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if not value.isdigit() or int(value) > 1440:
        await update.message.reply_text("Informe minutos entre 0 e 1440."); return ITEM_REMINDER
    context.user_data["new_daily_item"]["reminder_minutes"] = int(value)
    await update.message.reply_text("Alguma observação? `-` se não houver.", parse_mode="Markdown")
    return ITEM_DETAILS


async def add_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("new_daily_item")
    detail = (update.message.text or "").strip()
    add_item(data["kind"], data["title"], data.get("due_date"), data.get("due_time"),
             None if detail == "-" else detail, data.get("reminder_minutes", 10))
    await update.message.reply_text("✅ Salvo. Eu cuido do lembrete.", reply_markup=_menu(data["kind"]))
    return ConversationHandler.END


async def list_kind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kind = _kind_from_text(update.message.text or "")
    rows = list_items(kind=kind)
    if not rows:
        await update.message.reply_text("Nada pendente por aqui.", reply_markup=_menu(kind)); return
    parts = [f"{LABELS[kind][0]} *{LABELS[kind][2]} pendentes*\n"]
    for r in rows:
        when = ""
        if r["due_date"]: when += " — " + datetime.fromisoformat(r["due_date"]).strftime("%d/%m/%Y")
        if r["due_time"]: when += f" às {r['due_time']}"
        parts.append(f"`#{r['id']}` *{r['title']}*{when}")
        if r["details"]: parts.append(f"   {r['details']}")
        if r["due_time"]: parts.append(f"   🔔 {r['reminder_minutes']} min antes")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=_menu(kind))


async def select_start(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> int:
    kind = _kind_from_text(update.message.text or "")
    rows = list_items(kind=kind)
    if not rows:
        await update.message.reply_text("Não há itens pendentes.", reply_markup=_menu(kind)); return ConversationHandler.END
    context.user_data["daily_action"] = {"kind": kind, "action": action}
    listing = "\n".join(f"#{r['id']} — {r['title']}" for r in rows)
    await update.message.reply_text(f"Qual item? Digite o número.\n\n{listing}", reply_markup=ReplyKeyboardRemove())
    return {"complete": COMPLETE_ID, "edit": EDIT_ID, "delete": DELETE_ID}[action]


async def complete_start(update: Update, context: ContextTypes.DEFAULT_TYPE): return await select_start(update, context, "complete")
async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE): return await select_start(update, context, "edit")
async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE): return await select_start(update, context, "delete")


async def complete_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lstrip("#")
    data = context.user_data.pop("daily_action")
    if not value.isdigit() or not complete_item(int(value)):
        await update.message.reply_text("Não encontrei esse item.", reply_markup=_menu(data["kind"])); return ConversationHandler.END
    await update.message.reply_text("✅ Feito. Pode deixar que eu tiro isso da sua frente.", reply_markup=_menu(data["kind"]))
    return ConversationHandler.END


async def edit_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lstrip("#")
    if not value.isdigit() or not get_item(int(value)):
        await update.message.reply_text("Número inválido."); return EDIT_ID
    context.user_data["daily_action"]["id"] = int(value)
    kb = ReplyKeyboardMarkup([["Título", "Data"], ["Horário", "Lembrete"], ["Observação"]], resize_keyboard=True)
    await update.message.reply_text("O que mudou?", reply_markup=kb)
    return EDIT_FIELD


async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = (update.message.text or "").strip().lower()
    allowed = {"título":"title", "titulo":"title", "data":"due_date", "horário":"due_time", "horario":"due_time", "lembrete":"reminder_minutes", "observação":"details", "observacao":"details"}
    if field not in allowed:
        await update.message.reply_text("Escolha uma das opções."); return EDIT_FIELD
    context.user_data["daily_action"]["field"] = allowed[field]
    await update.message.reply_text("Informe o novo valor:", reply_markup=ReplyKeyboardRemove())
    return EDIT_VALUE


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("daily_action")
    value = (update.message.text or "").strip()
    field = data["field"]
    kwargs = {}
    if field == "due_date":
        parsed = _parse_date(value)
        if parsed is False: await update.message.reply_text("Data inválida.", reply_markup=_menu(data["kind"])); return ConversationHandler.END
        kwargs[field] = parsed
    elif field == "due_time":
        parsed = _parse_time(value)
        if parsed is False: await update.message.reply_text("Horário inválido.", reply_markup=_menu(data["kind"])); return ConversationHandler.END
        kwargs[field] = parsed
    elif field == "reminder_minutes":
        if not value.isdigit(): await update.message.reply_text("Informe minutos.", reply_markup=_menu(data["kind"])); return ConversationHandler.END
        kwargs[field] = int(value)
    elif field == "details": kwargs[field] = None if value == "-" else value
    else: kwargs[field] = value
    update_item(data["id"], **kwargs)
    await update.message.reply_text("✏️ Atualizado.", reply_markup=_menu(data["kind"]))
    return ConversationHandler.END


async def delete_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lstrip("#")
    if not value.isdigit() or not get_item(int(value)):
        await update.message.reply_text("Número inválido."); return DELETE_ID
    context.user_data["daily_action"]["id"] = int(value)
    await update.message.reply_text("Remover definitivamente?", reply_markup=ReplyKeyboardMarkup([["✅ Sim", "❌ Não"]], resize_keyboard=True))
    return DELETE_CONFIRM


async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("daily_action")
    if (update.message.text or "") == "✅ Sim":
        delete_item(data["id"]); text = "🗑️ Removido."
    else: text = "Tudo bem, mantive o item."
    await update.message.reply_text(text, reply_markup=_menu(data["kind"]))
    return ConversationHandler.END


async def reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q: return
    await q.answer()
    parts = q.data.split(":")
    action, item_id = parts[0], int(parts[1])
    if action == "daily_done":
        complete_item(item_id)
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text("✅ Certo. Marquei como concluído.")
    elif action == "daily_snooze":
        minutes = int(parts[2])
        snooze_item(item_id, (datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="minutes"))
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(f"⏰ Tudo bem. Volto a te lembrar em {minutes} minutos.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("new_daily_item", None); context.user_data.pop("daily_action", None)
    await update.message.reply_text("Operação cancelada.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


def register_lifestyle_handlers(application) -> None:
    add_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ (Nova tarefa|Novo compromisso|Nova pendência)$"), add_start)],
        states={ITEM_TITLE:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)], ITEM_DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_date)], ITEM_TIME:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_time)], ITEM_REMINDER:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder)], ITEM_DETAILS:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_details)]},
        fallbacks=[CommandHandler("cancelar", cancel)])
    complete_conv = ConversationHandler(entry_points=[MessageHandler(filters.Regex(r"^☑️ (Concluir tarefa|Concluir compromisso|Resolver pendência)$"), complete_start)], states={COMPLETE_ID:[MessageHandler(filters.TEXT & ~filters.COMMAND, complete_id)]}, fallbacks=[CommandHandler("cancelar", cancel)])
    edit_conv = ConversationHandler(entry_points=[MessageHandler(filters.Regex(r"^✏️ (Editar tarefa|Editar compromisso|Editar pendência)$"), edit_start)], states={EDIT_ID:[MessageHandler(filters.TEXT & ~filters.COMMAND, edit_id)], EDIT_FIELD:[MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field)], EDIT_VALUE:[MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)]}, fallbacks=[CommandHandler("cancelar", cancel)])
    delete_conv = ConversationHandler(entry_points=[MessageHandler(filters.Regex(r"^🗑️ (Remover tarefa|Remover compromisso|Remover pendência)$"), delete_start)], states={DELETE_ID:[MessageHandler(filters.TEXT & ~filters.COMMAND, delete_id)], DELETE_CONFIRM:[MessageHandler(filters.TEXT & ~filters.COMMAND, delete_confirm)]}, fallbacks=[CommandHandler("cancelar", cancel)])
    application.add_handler(add_conv, group=-1); application.add_handler(complete_conv, group=-1); application.add_handler(edit_conv, group=-1); application.add_handler(delete_conv, group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^(✅ Tarefas|📅 Compromissos|📌 Pendências)$"), open_kind_menu), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^📋 Ver (tarefas|compromissos|pendências)$"), list_kind), group=-1)
    application.add_handler(CallbackQueryHandler(reminder_callback, pattern=r"^daily_(done|snooze):"), group=-1)
