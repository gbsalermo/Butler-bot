"""Manual curto do usuário acessível dentro do Telegram.

O manual completo e versionado fica em ``docs/MANUAL_USUARIO.md``. Este módulo
mantém apenas lembretes operacionais curtos para não estourar o limite de mensagem
do Telegram nem duplicar documentação extensa no runtime.
"""

from __future__ import annotations

import language_primitives as language
from telegram_api import send_message


MANUAL_OPEN = {
    "/manual",
    "/ajuda",
    "manual",
    "ajuda",
    "como usa",
    "como usar",
    "o que voce faz",
    "o que você faz",
    "📖 manual",
    "📖 manual do butler",
}

SECTION_ALIASES = {
    "tempo": "tempo",
    "timer": "tempo",
    "cronometro": "tempo",
    "cronômetro": "tempo",
    "estudo": "estudo",
    "modo estudo": "estudo",
    "agenda": "agenda",
    "tarefas": "agenda",
    "compromissos": "agenda",
    "faculdade": "faculdade",
    "materias": "faculdade",
    "matérias": "faculdade",
    "ru": "faculdade",
    "minha vida": "cotidiano",
    "casa": "cotidiano",
    "interesses": "cotidiano",
    "cotidiano": "cotidiano",
    "mercado": "cotidiano",
    "rotinas": "cotidiano",
    "metas": "cotidiano",
    "treino": "treino",
    "musculacao": "treino",
    "musculação": "treino",
    "day off": "dayoff",
    "day-off": "dayoff",
}

MANUAL_KB = {
    "keyboard": [
        ["⏱️ Ajuda: Tempo", "📚 Ajuda: Estudo"],
        ["🗓️ Ajuda: Agenda", "🎓 Ajuda: Faculdade"],
        ["📋 Ajuda: Minha vida", "🏋️ Ajuda: Treino"],
        ["🌙 Ajuda: Day-off", "⬅️ Início"],
    ],
    "resize_keyboard": True,
}


def _norm(text):
    return language.normalize_text(language.strip_butler(text))


def _section_from_text(text):
    """Resolve seção apenas quando o usuário pediu ajuda explicitamente.

    Não aceitar aliases crus aqui é essencial porque este handler roda antes dos
    menus operacionais. Sem esse gate, botões de navegação poderiam ser
    confundidos com categorias do manual.
    """
    n = _norm(text)
    requested = False
    for prefix in ("ajuda: ", "ajuda "):
        if n.startswith(prefix):
            n = n[len(prefix):].strip()
            requested = True
            break
    if not requested:
        return None
    return SECTION_ALIASES.get(n)


def _overview():
    return (
        "📖 Manual rápido do Butler\n\n"
        "Você pode falar naturalmente; não precisa decorar comandos. "
        "A tela inicial fica enxuta: Faculdade, Minha vida, Treino e Mais; "
        "Adicionar e Hoje continuam como atalhos.\n\n"
        "Exemplos:\n"
        "📝 `cria uma tarefa revisar cálculo amanhã às 20h`\n"
        "📅 `tenho dentista sexta às 14h`\n"
        "🔔 `me lembra amanhã às 9h de levar o documento`\n"
        "⏱️ `me lembra de desligar o ovo daqui a 5 minutos`\n"
        "⏲️ `cronometra 20 minutos`\n"
        "📚 `modo estudo Cálculo I: limites, derivadas`\n"
        "🍽️ `qual o almoço hoje?`\n"
        "🏋️ `qual meu treino hoje?`\n\n"
        "Se estiver no meio de um fluxo: `Cancelar ação`."
    )


def _section_text(section):
    if section == "tempo":
        return (
            "⏱️ Tempo e cronômetros\n\n"
            "Alerta rápido:\n"
            "`me lembra de desligar o ovo daqui a 5 minutos`\n"
            "`tenho que ligar para João daqui a 10 minutos`\n\n"
            "Cronômetro:\n"
            "`cronometra 30 minutos`\n"
            "`inicia um timer de 45 segundos`\n\n"
            "Cancelar:\n"
            "`cancelar timer`\n"
            "Se houver vários, o Butler lista os IDs; depois use "
            "`cancelar timer #12`.\n\n"
            "Alertas rápidos vão de 1 segundo a 24 horas e não viram tarefa."
        )
    if section == "estudo":
        return (
            "📚 Modo Estudo\n\n"
            "Você pode abrir `🎓 Faculdade → 🧠 Modo Estudo` para ajuda rápida ou iniciar por frase:\n"
            "`modo estudo Cálculo I: limites, derivadas, integrais`\n\n"
            "Padrão: 25 min foco / 5 min pausa / 15 min pausa longa.\n"
            "Personalizar: `modo estudo 50/10/20 Cálculo I: limites, derivadas`\n\n"
            "Durante:\n"
            "`status estudo`\n"
            "`concluí o tópico`\n"
            "`pular tópico`\n"
            "`não terminei`\n"
            "`pausar estudo`\n"
            "`retomar estudo`\n"
            "`cancelar estudo`\n"
            "`histórico de estudo`\n\n"
            "Importante: o fim do timer nunca conclui tópico sozinho."
        )
    if section == "agenda":
        return (
            "🗓️ Agenda, tarefas e compromissos\n\n"
            "`🗓️ Hoje` continua na tela inicial. Tarefas e compromissos ficam em `📋 Minha vida`.\n\n"
            "Tarefa: `cria uma tarefa revisar cálculo amanhã às 20h`\n"
            "Compromisso: `tenho dentista amanhã às 15h`\n"
            "Lembrete: `me lembra amanhã às 9h de levar o documento`\n\n"
            "Consultar:\n"
            "`o que tenho hoje?`\n"
            "`o que tenho amanhã?`\n"
            "`o que faço agora?`\n\n"
            "Referências curtas também funcionam em contexto recente, como "
            "`conclui a segunda` e `muda ela pra sexta`."
        )
    if section == "faculdade":
        return (
            "🎓 Faculdade\n\n"
            "Abra `🎓 Faculdade`. `📚 Matérias` reúne matérias, provas, faltas e importação da grade.\n"
            "`🍽️ RU` consulta o cardápio e `🧠 Modo Estudo` abre a ajuda de estudo.\n"
            "Importação acadêmica aceita TXT ou PDF com texto pesquisável/selecionável.\n"
            "Fonte recomendada no SIGAA: `Componente Curricular | Local | Horário`.\n\n"
            "Provas: `tenho prova de cálculo sexta`.\n"
            "RU: `🎓 Faculdade → 🍽️ RU` ou pergunte `qual o almoço hoje?` / `qual o café amanhã?`.\n\n"
            "O Butler não presume presença só porque a aula aconteceu."
        )
    if section == "cotidiano":
        return (
            "📋 Minha vida\n\n"
            "Tarefas e compromissos ficam direto nessa área.\n"
            "Rotinas: `📋 Minha vida → 🧘 Rotinas`\n"
            "Metas: `📋 Minha vida → 🎯 Metas`\n"
            "Casa/mercado: `📋 Minha vida → 🛒 Casa`\n"
            "Interesses para depois: `📋 Minha vida → 📌 Interesses`\n\n"
            "Você também pode falar: `acabou café`, `tô sem detergente`, `o que está faltando?`.\n"
            "Clima continua por linguagem natural, por exemplo `vai chover amanhã?`.\n\n"
            "Rotina é recorrente; tarefa é pontual."
        )
    if section == "treino":
        return (
            "🏋️ Treino\n\n"
            "Abra `🏋️ Treino`. Ele entra direto no menu de musculação, sem submenu intermediário.\n"
            "Principais ações:\n"
            "`📅 Treino de hoje`\n"
            "`🚀 Começar os trabalhos` quando disponível no seu perfil\n"
            "`📝 Registrar série`\n"
            "`🔁 Substituir exercício`\n"
            "`✅ Finalizar treino`\n"
            "`😕 Não consegui treinar hoje`\n"
            "`📈 Progresso`\n\n"
            "Carga, repetições e conclusão só são registradas quando você informa."
        )
    if section == "dayoff":
        return (
            "🌙 Day-off\n\n"
            "Use `🌙 Day-off` para suspender o comportamento normal do dia. "
            "Ele continua sozinho na última linha da tela inicial e não é automático em fins de semana.\n\n"
            "Cronômetros/alertas rápidos explicitamente iniciados e uma sessão "
            "de estudo já aberta continuam funcionando."
        )
    return _overview()


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    if not text:
        return False
    n = _norm(text)
    section = _section_from_text(text)
    if n not in {_norm(x) for x in MANUAL_OPEN} and section is None:
        return False
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    await send_message(
        token,
        int(chat_id),
        _section_text(section) if section else _overview(),
        reply_markup=MANUAL_KB,
    )
    return True
