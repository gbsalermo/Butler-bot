"""Fast path conservador para ações operacionais do Butler.

Somente ações claras do núcleo passam por aqui. Botões exatos têm prioridade
sobre linguagem natural para nunca virarem títulos acidentalmente.
"""
import re
import unicodedata

import app
import runtime_guard
from colloquial_reminder_fastpath import handle_message as handle_colloquial_reminder
from exam_phrase_patch import handle_message as handle_exam_phrase
from grocery_phrase_patch import handle_message as handle_grocery
from natural_behavior_patch import handle_explicit_simple_reminder
from operational_informal_fastpath import handle_message as handle_informal_action
from routine_natural_fastpath import handle_message as handle_natural_routine
from task_context_patch import handle_message as handle_task_context
from ux_bugfixes import handle_global_navigation
from workout_progress_patch import handle_message as handle_workout_progress, install as install_workout_progress

install_workout_progress()

CORE_BUTTONS = {
    "adicionar","tarefa","tarefas","compromisso","compromissos","hoje","amanha",
    "outra data","proximos 7 dias","historico","item faltando","o que esta faltando",
    "adicionar item","ver itens faltando","cotidiano","musculacao","treino de hoje",
    "comecar os trabalhos","registrar serie","substituir exercicio","finalizar treino",
    "nao consegui treinar hoje","progresso","historico de cargas","reiniciar treinos",
    "menu principal","cancelar acao","materias","minhas materias","rotinas","metas",
}

CORE_HINTS = (
    # lembretes / tarefas
    "me lembra", "me avisa", "me da um toque", "não deixa eu esquecer", "nao deixa eu esquecer",
    "recorda", "lembra eu", "cria um lembrete", "crie um lembrete", "faz um lembrete", "anota um lembrete",
    "cria uma tarefa", "crie uma tarefa", "faz uma tarefa", "adiciona uma tarefa", "adicione uma tarefa",
    "anota uma tarefa", "bota como tarefa", "marca como tarefa", "tenho que", "tenho de", "preciso",
    # compromissos
    "marca um compromisso", "marque um compromisso", "cria um compromisso", "crie um compromisso",
    "adiciona compromisso", "anota compromisso", "tenho consulta", "tenho dentista", "tenho reuniao",
    "tenho reunião", "tenho entrevista", "consulta", "dentista", "reuniao", "reunião", "entrevista",
    # rotinas
    "cria uma rotina", "crie uma rotina", "faz uma rotina", "adiciona uma rotina", "adicione uma rotina",
    "quero adicionar uma rotina", "quero criar uma rotina", "cadastra uma rotina", "nova rotina", "rotina de",
    # agenda
    "minha agenda", "o que tenho hoje", "o que tenho amanha", "o que tenho amanhã",
    "o que tenho agendado", "agenda de hoje", "agenda de amanha", "agenda de amanhã",
    # acadêmico
    "prova de", "tenho prova", "marca a prova", "marca prova", "anota a prova", "agenda prova",
    "minhas faltas", "quantas faltas", "minhas materias", "minhas matérias",
    # mercado
    "item faltando", "o que esta faltando", "o que está faltando", "bota na lista",
    "coloca na lista", "adiciona na lista", "quero adicionar", "acabou", "cabou", "to sem", "tô sem", "comprar",
    # musculação
    "treino de hoje", "qual treino", "comecar os trabalhos", "começar os trabalhos",
    "registrar serie", "registrar série", "finalizar treino", "nao consegui treinar", "não consegui treinar",
    "historico de cargas", "histórico de cargas", "cargas anteriores", "progresso de cargas",
)


def _norm(text):
    v=unicodedata.normalize("NFKD",(text or "").lower())
    v="".join(c for c in v if not unicodedata.combining(c))
    v=re.sub(r"[^a-z0-9 ]+"," ",v)
    return re.sub(r"\s+"," ",v).strip()


def _looks_compound(n):
    groups=0
    checks=(
        ("tarefa","lembra","avisa","compromisso","agenda"),
        ("rotina",),
        ("treino","musculacao","serie"),
        ("materia","aula","prova","faltar","faltas"),
        ("lista","item faltando","acabou","to sem","comprar"),
    )
    for terms in checks:
        if any(t in n for t in terms):
            groups+=1
    return groups>=2 and len(n)>90


def _looks_temporal_followup(n):
    if n in ("hoje","amanha","segunda","terca","quarta","quinta","sexta","sabado","domingo"):
        return True
    if re.fullmatch(r"\d{1,2}(?:h\d{0,2}|:\d{2})?", n):
        return True
    if re.fullmatch(r"\d{1,2}/\d{1,2}(?:/\d{2,4})?", n):
        return True
    return False


def is_core_candidate(text):
    n=_norm(text)
    if not n or _looks_compound(n):
        return False
    stripped=re.sub(r"^butler\s+","",n).strip()
    if stripped in CORE_BUTTONS:
        return True
    return any(_norm(h) in n for h in CORE_HINTS)


async def handle_message(db,token,message):
    text=(message.get("text") or "").strip()
    n=_norm(text)
    stripped=re.sub(r"^butler\s+","",n).strip()

    # Navegação primeiro.
    if await handle_global_navigation(db,token,message):
        return True

    # Botão exato nunca passa por parser informal.
    if stripped in CORE_BUTTONS:
        await app.handle_message(db,token,message)
        return True

    # Respostas curtas de data/horário podem pertencer a um lembrete iniciado.
    if _looks_temporal_followup(n):
        if await handle_colloquial_reminder(db,token,message):
            return True

    if not is_core_candidate(text):
        return False

    if await handle_explicit_simple_reminder(db,token,message):return True
    if await handle_colloquial_reminder(db,token,message):return True
    if await handle_exam_phrase(db,token,message):return True
    if await handle_natural_routine(db,token,message):return True
    if await handle_informal_action(db,token,message):return True
    if await handle_task_context(db,token,message):return True
    if await handle_workout_progress(db,token,message):return True
    if await runtime_guard.handle_pre_dispatch(db,token,message):return True
    if await handle_grocery(db,token,message):return True
    return False
