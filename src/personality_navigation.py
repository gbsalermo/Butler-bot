import random

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

from src.daily_store import list_items
from src.ui_layout import COTIDIANO_KEYBOARD


COTIDIANO_LINES = [
    "Aqui ficam as pequenas coisas que costumam virar problema justamente porque ninguém lembra delas.",
    "Casa, metas, rotinas e dinheiro. A gloriosa administração da vida adulta.",
    "A área onde eu tento impedir que você descubra que acabou o café só quando já está sem café.",
    "Cotidiano, chefe. Porque aparentemente existir também exige gerenciamento de projeto.",
]

KIND_CONFIG = {
    "✅ Tarefas": {
        "kind": "tarefa",
        "title": "✅ *Tarefas*",
        "add": "➕ Nova tarefa",
        "view": "📋 Ver tarefas",
        "complete": "☑️ Concluir tarefa",
        "edit": "✏️ Editar tarefa",
        "remove": "🗑️ Remover tarefa",
        "empty": [
            "Nenhuma tarefa pendente. Vou registrar este raro momento histórico.",
            "Nada pendente aqui. Estranhamente eficiente, chefe.",
        ],
        "normal": [
            "Temos {count} tarefa(s) pendente(s). Ainda está civilizado.",
            "{count} tarefa(s) esperando. Elas parecem confiantes de que você vai aparecer.",
        ],
        "many": [
            "{count} tarefas. Isso já está começando a parecer uma coleção.",
            "{count} tarefas pendentes. Chefe, a fila ganhou personalidade própria.",
        ],
    },
    "📅 Compromissos": {
        "kind": "compromisso",
        "title": "📅 *Compromissos*",
        "add": "➕ Novo compromisso",
        "view": "📋 Ver compromissos",
        "complete": "☑️ Concluir compromisso",
        "edit": "✏️ Editar compromisso",
        "remove": "🗑️ Remover compromisso",
        "empty": ["Agenda limpa. Não se acostume."],
        "normal": ["{count} compromisso(s) registrado(s). Pelo menos agora temos testemunha."],
        "many": ["{count} compromissos. Excelente, aparentemente descansar virou atividade extracurricular."],
    },
    "📌 Pendências": {
        "kind": "pendencia",
        "title": "📌 *Pendências*",
        "add": "➕ Nova pendência",
        "view": "📋 Ver pendências",
        "complete": "☑️ Resolver pendência",
        "edit": "✏️ Editar pendência",
        "remove": "🗑️ Remover pendência",
        "empty": ["Nenhuma pendência. Eu sabia que esse dia chegaria. Só não esperava estar vivo para ver."],
        "normal": ["{count} pendência(s). Nada que exija decretar estado de calamidade."],
        "many": ["{count} pendências. Isso já ultrapassou organização e entrou em arqueologia."],
    },
}


async def cotidiano(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        f"🏠 *Cotidiano*\n\n{random.choice(COTIDIANO_LINES)}",
        parse_mode="Markdown",
        reply_markup=COTIDIANO_KEYBOARD,
    )
    raise ApplicationHandlerStop


def _kind_keyboard(config: dict) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [config["add"], config["view"]],
            [config["complete"], config["edit"]],
            [config["remove"], "🏠 Menu principal"],
        ],
        resize_keyboard=True,
    )


async def daily_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    config = KIND_CONFIG.get(update.message.text or "")
    if not config:
        return

    count = len(list_items(kind=config["kind"]))
    if count == 0:
        line = random.choice(config["empty"])
    elif count >= 6:
        line = random.choice(config["many"]).format(count=count)
    else:
        line = random.choice(config["normal"]).format(count=count)

    await update.message.reply_text(
        f"{config['title']}\n\n{line}",
        parse_mode="Markdown",
        reply_markup=_kind_keyboard(config),
    )
    raise ApplicationHandlerStop


def register_personality_navigation(application) -> None:
    application.add_handler(
        MessageHandler(filters.Regex(r"^(🏠 Cotidiano|⬅️ Voltar ao cotidiano)$"), cotidiano),
        group=-6,
    )
    application.add_handler(
        MessageHandler(filters.Regex(r"^(✅ Tarefas|📅 Compromissos|📌 Pendências)$"), daily_section),
        group=-6,
    )
