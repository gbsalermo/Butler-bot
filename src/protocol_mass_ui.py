from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes, MessageHandler, filters

import src.protocol_mass_handlers as protocol_handlers
from src.protocol_mass_store import get_state


PRE_PROTOCOL_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🚀 Começar os trabalhos"],
        ["🧪 Exemplo de treino"],
        ["⬅️ Voltar ao cotidiano"],
    ],
    resize_keyboard=True,
)

ACTIVE_PROTOCOL_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📅 Treino de hoje", "🏋️ Registrar séries"],
        ["🔁 Substituir exercício", "✅ Finalizar treino"],
        ["😕 Não consegui treinar hoje"],
        ["📈 Progresso Protocol Mass", "📊 Histórico de carga"],
        ["🔄 Reiniciar os trabalhos"],
        ["⬅️ Voltar ao cotidiano"],
    ],
    resize_keyboard=True,
)

# Os handlers existentes consultam PROTOCOL_KEYBOARD em tempo de execução.
# Durante um protocolo ativo, o menu diário nunca deve oferecer um novo início.
protocol_handlers.PROTOCOL_KEYBOARD = ACTIVE_PROTOCOL_KEYBOARD


async def open_protocol_mass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    state = get_state()
    if state["active"]:
        week = int(state["current_week"])
        await update.message.reply_text(
            f"🏋️ *Protocol Mass — Semana {week}/12*\n\n"
            "Os trabalhos já começaram. Agora eu acompanho o protocolo dia a dia, inclusive cada série, carga, repetição, substituição e falta.",
            parse_mode="Markdown",
            reply_markup=ACTIVE_PROTOCOL_KEYBOARD,
        )
    elif state["finished_at"]:
        await update.message.reply_text(
            "🏁 *Protocol Mass concluído.*\n\n"
            "As 12 semanas já foram encerradas. Durante os testes, você ainda pode usar o reinício para zerar o protocolo.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [["📈 Progresso Protocol Mass", "📊 Histórico de carga"], ["🔄 Reiniciar os trabalhos"], ["⬅️ Voltar ao cotidiano"]],
                resize_keyboard=True,
            ),
        )
    else:
        await update.message.reply_text(
            "🏋️ *Protocol Mass*\n\n"
            "As 12 semanas estão carregadas. *🚀 Começar os trabalhos* é o marco de início do protocolo inteiro e deve ser usado apenas uma vez.",
            parse_mode="Markdown",
            reply_markup=PRE_PROTOCOL_KEYBOARD,
        )

    raise ApplicationHandlerStop


async def block_duplicate_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Impede que 'Começar os trabalhos' seja reutilizado como início do treino diário."""
    state = get_state()
    if not state["active"]:
        return

    await update.message.reply_text(
        f"🕴️ Os trabalhos já estão em andamento — estamos na Semana {int(state['current_week'])}/12.\n\n"
        "Para o dia de hoje use *📅 Treino de hoje*. Se não conseguir treinar, registre *😕 Não consegui treinar hoje* e eu salvo a falta com o motivo.",
        parse_mode="Markdown",
        reply_markup=ACTIVE_PROTOCOL_KEYBOARD,
    )
    raise ApplicationHandlerStop


def register_protocol_mass_ui(application) -> None:
    application.add_handler(
        MessageHandler(filters.Regex(r"^(🏋️ Musculação|⬅️ Voltar à musculação)$"), open_protocol_mass),
        group=-4,
    )
    application.add_handler(
        MessageHandler(filters.Regex(r"^🚀 Começar os trabalhos$"), block_duplicate_start),
        group=-4,
    )
