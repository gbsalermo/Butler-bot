from datetime import date, datetime, timedelta

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationHandlerStop,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.daily_store import add_item, complete_item, list_items
from src.database import upsert_user

ITEM_TITLE, ITEM_DATE, ITEM_TIME, ITEM_DETAILS = range(100, 104)
COMPLETE_ID = 110

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📚 Matérias", "✅ Tarefas"],
        ["📅 Compromissos", "📌 Pendências"],
        ["💰 Finanças", "🗓️ Hoje"],
    ],
    resize_keyboard=True,
)

TASK_KEYBOARD = ReplyKeyboardMarkup(
    [["➕ Nova tarefa", "📋 Ver tarefas"], ["☑️ Concluir tarefa", "🏠 Menu principal"]],
    resize_keyboard=True,
)
COMMITMENT_KEYBOARD = ReplyKeyboardMarkup(
    [["➕ Novo compromisso", "📋 Ver compromissos"], ["☑️ Concluir compromisso", "🏠 Menu principal"]],
    resize_keyboard=True,
)
PENDING_KEYBOARD = ReplyKeyboardMarkup(
    [["➕ Nova pendência", "📋 Ver pendências"], ["☑️ Resolver pendência", "🏠 Menu principal"]],
    resize_keyboard=True,
)
FINANCE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["➕ Entrada", "➖ Gasto"],
        ["📊 Resumo do mês", "🎯 Metas financeiras"],
        ["📈 Histórico", "🏠 Menu principal"],
    ],
    resize_keyboard=True,
)

LABELS = {
    "tarefa": ("✅", "Tarefa", "Tarefas"),
    "compromisso": ("📅", "Compromisso", "Compromissos"),
    "pendencia": ("📌", "Pendência", "Pendências"),
}


def _kind_from_text(text: str) -> str | None:
    if "tarefa" in text.lower():
        return "tarefa"
    if "compromisso" in text.lower():
        return "compromisso"
    if "pendência" in text.lower() or "pendencia" in text.lower():
        return "pendencia"
    return None


def _parse_date(value: str) -> str | None | bool:
    normalized = value.strip().lower()
    today = date.today()
    if normalized in {"sem data", "-", "nenhuma"}:
        return None
    if normalized == "hoje":
        return today.isoformat()
    if normalized in {"amanhã", "amanha"}:
        return (today + timedelta(days=1)).isoformat()
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return False


def _parse_time(value: str) -> str | None | bool:
    normalized = value.strip().lower()
    if normalized in {"sem horário", "sem horario", "-", "nenhum"}:
        return None
    try:
        return datetime.strptime(value.strip(), "%H:%M").strftime("%H:%M")
    except ValueError:
        return False


def _menu_for_kind(kind: str) -> ReplyKeyboardMarkup:
    return {
        "tarefa": TASK_KEYBOARD,
        "compromisso": COMMITMENT_KEYBOARD,
        "pendencia": PENDING_KEYBOARD,
    }[kind]


async def home_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    user = update.effective_user
    upsert_user(update.effective_chat.id, user.id, user.first_name, user.username)
    await update.message.reply_text(
        "🕴️ *Butler à disposição.*\n\n"
        "Organizo sua rotina acadêmica e pessoal, acompanho tarefas e compromissos e já posso te avisar proativamente sobre horários cadastrados.\n\n"
        "Escolha uma área:",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    raise ApplicationHandlerStop


async def home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("🕴️ Menu principal do Butler.", reply_markup=MAIN_KEYBOARD)


async def subjects_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "📚 *Acadêmico*\n\n"
            "Use *📚 Minhas matérias* para consultar a grade ou *⚙️ Gerenciar matérias* para adicionar, remover, trancar e editar.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [["📚 Minhas matérias", "⚙️ Gerenciar matérias"], ["🏠 Menu principal"]],
                resize_keyboard=True,
            ),
        )


async def open_kind_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    kind = _kind_from_text(text)
    if not kind:
        return
    icon, singular, plural = LABELS[kind]
    await update.message.reply_text(
        f"{icon} *{plural}*\n\nAdicione, consulte ou conclua seus registros.",
        parse_mode="Markdown",
        reply_markup=_menu_for_kind(kind),
    )


async def add_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    kind = _kind_from_text(update.message.text or "")
    if not kind:
        return ConversationHandler.END
    context.user_data["new_daily_item"] = {"kind": kind}
    _, singular, _ = LABELS[kind]
    await update.message.reply_text(
        f"Qual é o título do(a) {singular.lower()}?\n\n/cancelar para sair.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ITEM_TITLE


async def item_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = (update.message.text or "").strip()
    if len(title) < 2:
        await update.message.reply_text("Informe um título válido.")
        return ITEM_TITLE
    context.user_data["new_daily_item"]["title"] = title
    await update.message.reply_text(
        "Para qual data?\n\nUse `DD/MM/AAAA`, `hoje`, `amanhã` ou `sem data`.",
        parse_mode="Markdown",
    )
    return ITEM_DATE


async def item_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parsed = _parse_date(update.message.text or "")
    if parsed is False:
        await update.message.reply_text("Data inválida. Ex.: `20/08/2026`, `amanhã` ou `sem data`.", parse_mode="Markdown")
        return ITEM_DATE
    context.user_data["new_daily_item"]["due_date"] = parsed
    await update.message.reply_text(
        "Qual o horário? Use `HH:MM` ou `sem horário`.\n\nItens com data e hora podem gerar aviso automático 10 minutos antes.",
        parse_mode="Markdown",
    )
    return ITEM_TIME


async def item_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parsed = _parse_time(update.message.text or "")
    if parsed is False:
        await update.message.reply_text("Horário inválido. Ex.: `14:30` ou `sem horário`.", parse_mode="Markdown")
        return ITEM_TIME
    context.user_data["new_daily_item"]["due_time"] = parsed
    await update.message.reply_text("Algum detalhe/observação? Digite `-` se não houver.", parse_mode="Markdown")
    return ITEM_DETAILS


async def item_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    details = (update.message.text or "").strip()
    data = context.user_data["new_daily_item"]
    add_item(
        kind=data["kind"],
        title=data["title"],
        due_date=data.get("due_date"),
        due_time=data.get("due_time"),
        details=None if details == "-" else details,
        reminder_minutes=10,
    )
    icon, singular, _ = LABELS[data["kind"]]
    await update.message.reply_text(
        f"{icon} *{singular} registrado(a).*",
        parse_mode="Markdown",
        reply_markup=_menu_for_kind(data["kind"]),
    )
    context.user_data.pop("new_daily_item", None)
    return ConversationHandler.END


async def list_kind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kind = _kind_from_text(update.message.text or "")
    if not kind:
        return
    rows = list_items(kind=kind, only_pending=True)
    icon, _, plural = LABELS[kind]
    if not rows:
        await update.message.reply_text(f"{icon} Nenhum item pendente em {plural.lower()}.", reply_markup=_menu_for_kind(kind))
        return
    parts = [f"{icon} *{plural} pendentes*\n"]
    for row in rows:
        when = ""
        if row["due_date"]:
            d = datetime.fromisoformat(row["due_date"]).strftime("%d/%m/%Y")
            when = f" — {d}"
        if row["due_time"]:
            when += f" às {row['due_time']}"
        parts.append(f"`#{row['id']}` *{row['title']}*{when}")
        if row["details"]:
            parts.append(f"   {row['details']}")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=_menu_for_kind(kind))


async def complete_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    kind = _kind_from_text(update.message.text or "")
    if not kind:
        return ConversationHandler.END
    context.user_data["complete_kind"] = kind
    rows = list_items(kind=kind, only_pending=True)
    if not rows:
        await update.message.reply_text("Não há itens pendentes para concluir.", reply_markup=_menu_for_kind(kind))
        return ConversationHandler.END
    text = "\n".join(f"#{row['id']} — {row['title']}" for row in rows)
    await update.message.reply_text(
        f"Qual item foi concluído/resolvido? Digite o número.\n\n{text}",
        reply_markup=ReplyKeyboardRemove(),
    )
    return COMPLETE_ID


async def complete_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lstrip("#")
    kind = context.user_data.get("complete_kind", "tarefa")
    if not value.isdigit():
        await update.message.reply_text("Digite apenas o número do item, por exemplo `3`.", parse_mode="Markdown")
        return COMPLETE_ID
    if complete_item(int(value)):
        await update.message.reply_text("✅ Marcado como concluído/resolvido.", reply_markup=_menu_for_kind(kind))
    else:
        await update.message.reply_text("Não encontrei um item pendente com esse número.", reply_markup=_menu_for_kind(kind))
    context.user_data.pop("complete_kind", None)
    return ConversationHandler.END


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today_iso = date.today().isoformat()
    rows = [row for row in list_items(only_pending=True) if row["due_date"] == today_iso]
    if not rows:
        await update.message.reply_text("🗓️ Nenhuma tarefa, compromisso ou pendência registrada para hoje.", reply_markup=MAIN_KEYBOARD)
        return
    parts = ["🗓️ *Seu dia*\n"]
    for row in rows:
        icon, singular, _ = LABELS[row["kind"]]
        hour = f" {row['due_time']} —" if row["due_time"] else ""
        parts.append(f"{icon}{hour} *{row['title']}* ({singular.lower()})")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def finance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = update.message.text or ""
    if text == "💰 Finanças":
        await update.message.reply_text(
            "💰 *Finanças do Butler*\n\n"
            "Este módulo está preparado como a próxima frente de evolução. A ideia é o Butler acompanhar seu dinheiro do mesmo jeito que acompanha sua agenda:\n\n"
            "• entradas e saídas;\n"
            "• gastos por categoria;\n"
            "• total e saldo do mês;\n"
            "• comparação com meses anteriores;\n"
            "• detecção de aumento/exagero em categorias;\n"
            "• valor economizado;\n"
            "• metas de economia e compras;\n"
            "• avisos quando o ritmo de gasto estiver acima do normal.",
            parse_mode="Markdown",
            reply_markup=FINANCE_KEYBOARD,
        )
        return
    await update.message.reply_text(
        "💰 Essa função financeira já está prevista no Butler, mas ainda não registra valores nesta versão.",
        reply_markup=FINANCE_KEYBOARD,
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("new_daily_item", None)
    kind = data.get("kind") if data else context.user_data.pop("complete_kind", None)
    await update.message.reply_text("Operação cancelada.", reply_markup=_menu_for_kind(kind) if kind else MAIN_KEYBOARD)
    return ConversationHandler.END


def register_lifestyle_handlers(application) -> None:
    # Grupo -1 permite que o novo /start substitua o menu antigo do módulo acadêmico.
    application.add_handler(CommandHandler("start", home_start), group=-1)
    application.add_handler(CommandHandler("menu", home), group=-1)

    add_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^➕ Nova tarefa$"), add_item_start),
            MessageHandler(filters.Regex(r"^➕ Novo compromisso$"), add_item_start),
            MessageHandler(filters.Regex(r"^➕ Nova pendência$"), add_item_start),
        ],
        states={
            ITEM_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_title)],
            ITEM_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_date)],
            ITEM_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_time)],
            ITEM_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, item_details)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )
    complete_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^☑️ Concluir tarefa$"), complete_start),
            MessageHandler(filters.Regex(r"^☑️ Concluir compromisso$"), complete_start),
            MessageHandler(filters.Regex(r"^☑️ Resolver pendência$"), complete_start),
        ],
        states={COMPLETE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, complete_id)]},
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    application.add_handler(add_conversation, group=-1)
    application.add_handler(complete_conversation, group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^🏠 Menu principal$"), home), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^📚 Matérias$"), subjects_menu), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^(✅ Tarefas|📅 Compromissos|📌 Pendências)$"), open_kind_menu), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^(📋 Ver tarefas|📋 Ver compromissos|📋 Ver pendências)$"), list_kind), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^🗓️ Hoje$"), today), group=-1)
    application.add_handler(MessageHandler(filters.Regex(r"^(💰 Finanças|➕ Entrada|➖ Gasto|📊 Resumo do mês|🎯 Metas financeiras|📈 Histórico)$"), finance), group=-1)
