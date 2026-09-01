"""Fast path conservador para ações operacionais do Butler.

Somente ações claras do núcleo passam por aqui. Botões exatos são diferenciados
de respostas digitadas como "hoje"/"amanhã" para não quebrar fluxos guiados.
"""
import re

import app
import language_primitives as language
import runtime_guard
from colloquial_reminder_fastpath import handle_message as handle_colloquial_reminder
from compound_router import handle_message as handle_compound_message, is_compound_action
from exam_phrase_patch import handle_message as handle_exam_phrase
from grocery_phrase_patch import handle_message as handle_grocery
from notification_ack import handle_message as handle_notification_ack
from operational_informal_fastpath import handle_message as handle_informal_action
from quick_time import handle_message as handle_quick_time
from routine_natural_fastpath import handle_message as handle_natural_routine
from study_mode import handle_message as handle_study_mode, install as install_study_mode
from task_context_patch import handle_message as handle_task_context
from ux_bugfixes import handle_global_navigation
from weather_context import handle_message as handle_weather_context
from workout_progress_patch import handle_message as handle_workout_progress, install as install_workout_progress

install_workout_progress()
install_study_mode()

CORE_BUTTONS = {
    "adicionar", "tarefa", "tarefas", "compromisso", "compromissos", "hoje", "amanha",
    "outra data", "proximos 7 dias", "historico", "item faltando", "o que esta faltando",
    "adicionar item", "ver itens faltando", "cotidiano", "musculacao", "treino de hoje",
    "comecar os trabalhos", "registrar serie", "substituir exercicio", "finalizar treino",
    "nao consegui treinar hoje", "progresso", "historico de cargas", "reiniciar treinos",
    "menu principal", "cancelar acao", "materias", "minhas materias", "rotinas", "metas",
}

EXACT_BUTTONS = {
    "➕ Adicionar", "✅ Tarefa", "✅ Tarefas", "📅 Compromisso", "📅 Compromissos",
    "🗓️ Hoje", "⏭️ Amanhã", "📆 Outra data", "🗓️ Próximos 7 dias", "📚 Histórico",
    "🛒 Item faltando", "🛒 O que está faltando?", "➕ Item faltando", "➕ Adicionar item",
    "📋 Ver itens faltando", "🏠 Cotidiano", "🏋️ Musculação", "📅 Treino de hoje",
    "🚀 Começar os trabalhos", "📝 Registrar série", "🔁 Substituir exercício",
    "✅ Finalizar treino", "😕 Não consegui treinar hoje", "📈 Progresso",
    "🔄 Reiniciar treinos", "🏠 Menu principal", "❌ Cancelar ação", "📚 Matérias",
    "📚 Minhas matérias", "🧘 Rotinas", "🎯 Metas",
}

CORE_ACTION_FAMILIES = {
    "reminder", "create_task", "create_appointment", "create_routine",
    "complete", "cancel", "reschedule",
}

CORE_HINTS = (
    "minha agenda", "o que tenho hoje", "o que tenho amanha", "o que tenho amanhã",
    "o que tenho agendado", "agenda de hoje", "agenda de amanha", "agenda de amanhã",
    "prova de", "tenho prova", "marca a prova", "marca prova", "anota a prova", "agenda prova",
    "minhas faltas", "quantas faltas", "minhas materias", "minhas matérias",
    "item faltando", "o que esta faltando", "o que está faltando", "bota na lista",
    "coloca na lista", "adiciona na lista", "quero adicionar", "acabou", "cabou", "to sem", "tô sem", "comprar",
    "treino de hoje", "qual treino", "comecar os trabalhos", "começar os trabalhos",
    "registrar serie", "registrar série", "finalizar treino", "nao consegui treinar", "não consegui treinar",
    "historico de cargas", "histórico de cargas", "cargas anteriores", "progresso de cargas",
)


def _norm(text):
    return language.normalize_text(text)


def _looks_compound(text):
    return is_compound_action(text)


def _looks_temporal_followup(n):
    if n in ("hoje", "amanha", "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"):
        return True
    if re.fullmatch(r"\d{1,2}(?:h\d{0,2}|:\d{2})?", n):
        return True
    if re.fullmatch(r"\d{1,2}/\d{1,2}(?:/\d{2,4})?", n):
        return True
    return False


def _has_core_action(text):
    families = set(language.detect_action_families(text))
    for family in CORE_ACTION_FAMILIES:
        if family not in families:
            continue
        if family == "reminder" and not language.is_positive_action_request(text, "reminder"):
            continue
        return True
    return False


def is_core_candidate(text):
    n = _norm(text)
    if not n or _looks_compound(text):
        return False
    stripped = language.normalize_text(language.strip_butler(text))
    if stripped in CORE_BUTTONS:
        return True
    if _has_core_action(text):
        return True
    return any(_norm(hint) in n for hint in CORE_HINTS)


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    n = _norm(text)

    if await handle_global_navigation(db, token, message):
        return True

    if await handle_weather_context(db, token, message):
        return True

    if await handle_quick_time(db, token, message):
        return True

    # Modo Estudo tem precedência sobre respostas sociais. Assim `terminei`
    # durante uma sessão continua sendo progresso explícito do estudo.
    if await handle_study_mode(db, token, message):
        return True

    # Avisos efêmeros já terminaram quando são enviados. Uma resposta curta é
    # opcional e apenas fecha a conversa de forma natural.
    if await handle_notification_ack(db, token, message):
        return True

    if await handle_compound_message(db, token, message):
        return True

    if _looks_temporal_followup(n):
        if await handle_colloquial_reminder(db, token, message):
            return True

    if text in EXACT_BUTTONS:
        await app.handle_message(db, token, message)
        return True

    if not is_core_candidate(text):
        return False

    if await handle_colloquial_reminder(db, token, message):
        return True
    if await handle_exam_phrase(db, token, message):
        return True
    if await handle_natural_routine(db, token, message):
        return True
    if await handle_informal_action(db, token, message):
        return True
    if await handle_task_context(db, token, message):
        return True
    if await handle_workout_progress(db, token, message):
        return True
    if await runtime_guard.handle_pre_dispatch(db, token, message):
        return True
    if await handle_grocery(db, token, message):
        return True
    return False
