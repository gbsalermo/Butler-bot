from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.home_store import (
    add_later_item,
    get_later_item,
    list_later_items,
    remove_later_item,
    update_later_item,
)
from src.ui_layout import COTIDIANO_KEYBOARD

(
    LATER_ADD_CATEGORY,
    LATER_ADD_NAME,
    LATER_ADD_CUSTOM,
    LATER_EDIT_ID,
    LATER_EDIT_NAME,
    LATER_EDIT_CATEGORY,
    LATER_EDIT_CUSTOM,
    LATER_REMOVE_ID,
) = range(230, 238)

LATER_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["➕ Adicionar à lista", "📚 Livros"],
        ["🎬 Filmes", "🗂️ Outras"],
        ["✏️ Editar item", "🗑️ Remover item"],
        ["⬅️ Voltar ao cotidiano"],
    ],
    resize_keyboard=True,
)

CATEGORY_KEYBOARD = ReplyKeyboardMarkup(
    [["📚 Livro", "🎬 Filme", "🗂️ Outra"], ["❌ Cancelar"]],
    resize_keyboard=True,
)

EDIT_CATEGORY_KEYBOARD = ReplyKeyboardMarkup(
    [["📚 Livro", "🎬 Filme", "🗂️ Outra"], ["➖ Manter categoria", "❌ Cancelar"]],
    resize_keyboard=True,
)

CATEGORY_BY_BUTTON = {
    "📚 Livro": "LIVRO",
    "🎬 Filme": "FILME",
    "🗂️ Outra": "OUTRA",
}

CATEGORY_LABEL = {
    "LIVRO": "📚 Livro",
    "FILME": "🎬 Filme",
    "OUTRA": "🗂️ Outra",
}


def _item_label(row) -> str:
    label = CATEGORY_LABEL.get(row["category"], row["category"])
    if row["category"] == "OUTRA" and row["custom_category"]:
        label = f"🗂️ {row['custom_category']}"
    return f"#{row['id']} — {row['name']} [{label}]"


async def later_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📌 *Ler/ver depois*\n\n"
        "Uma lista simples para guardar coisas que você quer ler ou ver depois. "
        "Sem lembretes, datas ou ligação com tarefas.",
        parse_mode="Markdown",
        reply_markup=LATER_KEYBOARD,
    )


async def later_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["later_add"] = {}
    await update.message.reply_text("Em qual categoria entra?", reply_markup=CATEGORY_KEYBOARD)
    return LATER_ADD_CATEGORY


async def later_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    category = CATEGORY_BY_BUTTON.get(text)
    if not category:
        await update.message.reply_text("Escolha Livro, Filme ou Outra pelos botões abaixo.", reply_markup=CATEGORY_KEYBOARD)
        return LATER_ADD_CATEGORY

    context.user_data["later_add"]["category"] = category
    if category == "OUTRA":
        await update.message.reply_text(
            "Qual é o tipo? Ex.: `série`, `HQ`, `documentário`, `artigo`.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return LATER_ADD_CUSTOM

    await update.message.reply_text("O que você quer salvar?", reply_markup=ReplyKeyboardRemove())
    return LATER_ADD_NAME


async def later_add_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    custom = (update.message.text or "").strip()
    if len(custom) < 2:
        await update.message.reply_text("Informe um tipo válido.")
        return LATER_ADD_CUSTOM
    context.user_data["later_add"]["custom_category"] = custom
    await update.message.reply_text("O que você quer salvar?")
    return LATER_ADD_NAME


async def later_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if len(name) < 2:
        await update.message.reply_text("Informe um nome válido.")
        return LATER_ADD_NAME

    data = context.user_data.pop("later_add")
    item_id = add_later_item(name, data["category"], data.get("custom_category"))
    await update.message.reply_text(
        f"✅ Salvo na lista como #{item_id}: {name}",
        reply_markup=LATER_KEYBOARD,
    )
    return ConversationHandler.END


async def _list_category(update: Update, category: str) -> None:
    rows = list_later_items(category)
    if not rows:
        empty = {
            "LIVRO": "Nenhum livro salvo ainda.",
            "FILME": "Nenhum filme salvo ainda.",
            "OUTRA": "Nenhum item da categoria Outra salvo ainda.",
        }[category]
        await update.message.reply_text(empty, reply_markup=LATER_KEYBOARD)
        return

    title = {
        "LIVRO": "📚 *Livros para ler*",
        "FILME": "🎬 *Filmes para ver*",
        "OUTRA": "🗂️ *Outras coisas para depois*",
    }[category]
    lines = [title, ""]
    for row in rows:
        if category == "OUTRA":
            custom = row["custom_category"] or "Outra"
            lines.append(f"`#{row['id']}` • {row['name']} — {custom}")
        else:
            lines.append(f"`#{row['id']}` • {row['name']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=LATER_KEYBOARD)


async def later_list_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _list_category(update, "LIVRO")


async def later_list_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _list_category(update, "FILME")


async def later_list_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _list_category(update, "OUTRA")


async def later_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rows = list_later_items()
    if not rows:
        await update.message.reply_text("A lista está vazia.", reply_markup=LATER_KEYBOARD)
        return ConversationHandler.END

    text = "\n".join(_item_label(row) for row in rows)
    context.user_data.pop("later_edit", None)
    await update.message.reply_text(
        f"Qual item você quer editar? Digite o número.\n\n{text}",
        reply_markup=ReplyKeyboardRemove(),
    )
    return LATER_EDIT_ID


async def later_edit_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lstrip("#")
    if not value.isdigit():
        await update.message.reply_text("Digite apenas o número do item.")
        return LATER_EDIT_ID

    row = get_later_item(int(value))
    if not row:
        await update.message.reply_text("Não encontrei esse item. Tente outro número.")
        return LATER_EDIT_ID

    context.user_data["later_edit"] = {
        "id": int(row["id"]),
        "name": row["name"],
        "category": row["category"],
        "custom_category": row["custom_category"],
    }
    await update.message.reply_text(
        f"Nome atual: {row['name']}\n\nDigite o novo nome ou `-` para manter.",
        parse_mode="Markdown",
    )
    return LATER_EDIT_NAME


async def later_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip()
    if value != "-":
        if len(value) < 2:
            await update.message.reply_text("Informe um nome válido ou `-` para manter.", parse_mode="Markdown")
            return LATER_EDIT_NAME
        context.user_data["later_edit"]["name"] = value

    await update.message.reply_text("Quer mudar a categoria?", reply_markup=EDIT_CATEGORY_KEYBOARD)
    return LATER_EDIT_CATEGORY


async def later_edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    data = context.user_data["later_edit"]

    if text == "➖ Manter categoria":
        update_later_item(data["id"], data["name"], data["category"], data.get("custom_category"))
        context.user_data.pop("later_edit", None)
        await update.message.reply_text("✅ Item atualizado.", reply_markup=LATER_KEYBOARD)
        return ConversationHandler.END

    category = CATEGORY_BY_BUTTON.get(text)
    if not category:
        await update.message.reply_text("Escolha uma categoria pelos botões.", reply_markup=EDIT_CATEGORY_KEYBOARD)
        return LATER_EDIT_CATEGORY

    data["category"] = category
    if category == "OUTRA":
        await update.message.reply_text(
            "Qual é o tipo dessa categoria Outra? Ex.: `série`, `HQ`, `artigo`.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return LATER_EDIT_CUSTOM

    data["custom_category"] = None
    update_later_item(data["id"], data["name"], data["category"], None)
    context.user_data.pop("later_edit", None)
    await update.message.reply_text("✅ Item atualizado.", reply_markup=LATER_KEYBOARD)
    return ConversationHandler.END


async def later_edit_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    custom = (update.message.text or "").strip()
    if len(custom) < 2:
        await update.message.reply_text("Informe um tipo válido.")
        return LATER_EDIT_CUSTOM

    data = context.user_data.pop("later_edit")
    update_later_item(data["id"], data["name"], "OUTRA", custom)
    await update.message.reply_text("✅ Item atualizado.", reply_markup=LATER_KEYBOARD)
    return ConversationHandler.END


async def later_remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rows = list_later_items()
    if not rows:
        await update.message.reply_text("A lista está vazia.", reply_markup=LATER_KEYBOARD)
        return ConversationHandler.END

    text = "\n".join(_item_label(row) for row in rows)
    await update.message.reply_text(
        f"Qual item você quer remover? Digite o número.\n\n{text}",
        reply_markup=ReplyKeyboardRemove(),
    )
    return LATER_REMOVE_ID


async def later_remove_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = (update.message.text or "").strip().lstrip("#")
    if not value.isdigit():
        await update.message.reply_text("Digite apenas o número do item.")
        return LATER_REMOVE_ID

    if remove_later_item(int(value)):
        await update.message.reply_text("🗑️ Item removido da lista.", reply_markup=LATER_KEYBOARD)
    else:
        await update.message.reply_text("Não encontrei esse item.", reply_markup=LATER_KEYBOARD)
    return ConversationHandler.END


async def later_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("later_add", None)
    context.user_data.pop("later_edit", None)
    await update.message.reply_text("Operação cancelada.", reply_markup=LATER_KEYBOARD)
    return ConversationHandler.END


def register_later_handlers(application) -> None:
    cancel_handlers = [
        CommandHandler("cancelar", later_cancel),
        MessageHandler(filters.Regex(r"^❌ Cancelar$"), later_cancel),
    ]

    add_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ Adicionar à lista$"), later_add_start)],
        states={
            LATER_ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, later_add_category)],
            LATER_ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, later_add_name)],
            LATER_ADD_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, later_add_custom)],
        },
        fallbacks=cancel_handlers,
    )

    edit_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^✏️ Editar item$"), later_edit_start)],
        states={
            LATER_EDIT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, later_edit_id)],
            LATER_EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, later_edit_name)],
            LATER_EDIT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, later_edit_category)],
            LATER_EDIT_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, later_edit_custom)],
        },
        fallbacks=cancel_handlers,
    )

    remove_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🗑️ Remover item$"), later_remove_start)],
        states={LATER_REMOVE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, later_remove_id)]},
        fallbacks=cancel_handlers,
    )

    application.add_handler(add_conv, group=-2)
    application.add_handler(edit_conv, group=-2)
    application.add_handler(remove_conv, group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^📌 Ler/ver depois$"), later_menu), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^📚 Livros$"), later_list_books), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^🎬 Filmes$"), later_list_movies), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^🗂️ Outras$"), later_list_other), group=-2)
    application.add_handler(MessageHandler(filters.Regex(r"^⬅️ Voltar ao cotidiano$"), later_back_to_cotidiano), group=-2)


async def later_back_to_cotidiano(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🏠 Cotidiano", reply_markup=COTIDIANO_KEYBOARD)
