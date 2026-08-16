"""Fast path para o papel base do Butler.

Mensagens claramente funcionais não precisam atravessar memória, Library e conversa.
O fast path é conservador: mensagens compostas/ambíguas continuam no dispatcher completo.
"""
import re
import unicodedata

import app
import runtime_guard
from grocery_phrase_patch import handle_message as handle_grocery
from natural_behavior_patch import handle_explicit_simple_reminder
from task_context_patch import handle_message as handle_task_context
from ux_bugfixes import handle_global_navigation

CORE_BUTTONS = {
    "adicionar","tarefa","tarefas","compromisso","compromissos","hoje","amanha",
    "outra data","proximos 7 dias","historico","item faltando","o que esta faltando",
    "adicionar item","ver itens faltando","cotidiano","musculacao","treino de hoje",
    "comecar os trabalhos","registrar serie","substituir exercicio","finalizar treino",
    "nao consegui treinar hoje","progresso","reiniciar treinos","menu principal",
    "cancelar acao",
}

CORE_HINTS = (
    "me lembra", "me avisa", "cria um lembrete", "crie um lembrete",
    "cria uma tarefa", "crie uma tarefa", "adiciona uma tarefa", "adicione uma tarefa",
    "marca um compromisso", "marque um compromisso", "adiciona compromisso",
    "minha agenda", "o que tenho hoje", "o que tenho amanha", "o que tenho amanhã",
    "o que tenho agendado", "agenda de hoje", "agenda de amanha", "agenda de amanhã",
    "item faltando", "o que esta faltando", "o que está faltando", "bota na lista",
    "coloca na lista", "adiciona na lista", "treino de hoje", "qual treino",
    "comecar os trabalhos", "começar os trabalhos", "registrar serie", "registrar série",
    "finalizar treino", "nao consegui treinar", "não consegui treinar",
)


def _norm(text):
    v=unicodedata.normalize("NFKD",(text or "").lower())
    v="".join(c for c in v if not unicodedata.combining(c))
    v=re.sub(r"[^a-z0-9 ]+"," ",v)
    return re.sub(r"\s+"," ",v).strip()


def _looks_compound(n):
    # Mais de uma intenção forte na mesma frase deve ir ao Compound Router.
    groups=0
    checks=(
        ("receita","filme","serie","livro","jogo"),
        ("tarefa","lembra","avisa","compromisso","agenda"),
        ("treino","musculacao","serie"),
        ("materia","aula","prova","faltar","faltas"),
        ("lista","item faltando","acabou","to sem"),
    )
    for terms in checks:
        if any(t in n for t in terms): groups+=1
    return groups>=2 and len(n)>70


def is_core_candidate(text):
    n=_norm(text)
    if not n or _looks_compound(n): return False
    stripped=re.sub(r"^butler\s+","",n).strip()
    if stripped in CORE_BUTTONS:return True
    return any(_norm(h) in n for h in CORE_HINTS)


async def handle_message(db,token,message):
    text=(message.get("text") or "").strip()
    if not is_core_candidate(text):return False

    # Patches funcionais específicos têm prioridade e podem responder sem passar
    # pelo app monolítico.
    if await handle_global_navigation(db,token,message):return True
    if await handle_explicit_simple_reminder(db,token,message):return True
    if await handle_task_context(db,token,message):return True
    if await runtime_guard.handle_pre_dispatch(db,token,message):return True
    if await handle_grocery(db,token,message):return True

    # Para botões/menu/agenda/musculação, o app é a autoridade original.
    await app.handle_message(db,token,message)
    return True
