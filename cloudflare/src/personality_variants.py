import random
import re

import academic_intelligence
import quality_patch


def _pick(options):
    return random.choice(options)


def _rewrite(text):
    if not text:
        return text

    # Tarefas: mantém a informação operacional e varia a provocação.
    if text.startswith("✅ ") and "Faltam 10 minutos" in text:
        base = text.split("Faltam 10 minutos", 1)[0] + "Faltam 10 minutos. "
        return base + _pick([
            "Dá tempo de fazer. Também dá tempo de inventar desculpa, mas vamos tentar a primeira opção. 😌",
            "Dez minutos: a distância oficial entre 'tranquilo' e 'como assim já deu a hora?'.",
            "Estou avisando agora para daqui a pouco você não alegar abandono administrativo. 😏",
            "Seu eu de dez minutos no futuro agradece se você começar antes dele entrar em pânico.",
            "Considere isto a última saída antes da estação Procrastinação Central. 😌",
            "Não precisa correr. Só precisa, veja só, começar.",
            "Ainda dá tempo de resolver com dignidade. Depois disso eu não garanto a dignidade.",
            "O relógio começou a fazer aquela coisa inconveniente de continuar andando. 😏",
        ])

    # Compromissos: 5 minutos antes.
    if text.startswith("📅 ") and "Faltam 5 minutos" in text:
        base = text.split("Faltam 5 minutos", 1)[0] + "Faltam 5 minutos. "
        return base + _pick([
            "Se ainda não estiver pronto, chegou a fase científica conhecida como 'vai assim mesmo'. 😌",
            "Cinco minutos. Agora é uma excelente hora para descobrir onde você deixou tudo.",
            "Estou cumprindo minha parte. A parte de chegar no horário continua sendo sua. 😏",
            "Hora de ir. Sim, sair quando faltam cinco minutos costuma ajudar a chegar menos atrasado.",
            "Última chamada antes de você transformar atraso em traço de personalidade.",
            "Já pode começar a movimentação estratégica conhecida como levantar e ir. 😌",
            "Cinco minutos. Não é muito, mas ainda é mais planejamento do que deixar para lembrar sozinho.",
        ])

    # Lembretes simples.
    if text.startswith("🔔 ") and "Só um aviso" in text:
        base = text.split("Só um aviso", 1)[0]
        return base + _pick([
            "Só um aviso. Não precisa preencher relatório de conclusão, por incrível que pareça.",
            "Passando para lembrar, porque aparentemente memória também entrou na minha folha de pagamento. 😌",
            "Avisado. Daqui para frente a responsabilidade volta oficialmente para você.",
            "Pronto, lembrei. Agora não vale dizer que ninguém avisou. 😏",
            "Meu trabalho aqui era interromper sua paz por alguns segundos. Concluído.",
        ])

    # Confirmação parcial de rotina.
    if "checkpoint(s)" in text:
        head = text.split("checkpoint(s).", 1)[0] + "checkpoint(s). "
        return head + _pick([
            "Registrado. A rotina aceita atraso; o importante é não transformar atraso em desaparecimento. 😌",
            "Conta feita. Você atrasou, mas apareceu — já é uma relação mais saudável com a rotina.",
            "Anotado. Não sou fiscal de relógio; sou fiscal de você não esquecer completamente. 😏",
            "Registrado. Pontualidade perfeita fica para os relógios suíços; consistência já serve.",
        ])

    # Rotina concluída.
    if text.startswith("🏁 ") or (text.startswith("✅ ") and "Meta contabilizada" in text):
        return text + " " + _pick([
            "Olha só, uma obrigação concluída sem precisar de intervenção federal. 😌",
            "Muito bem. Vou arquivar este raro evento para fins históricos. 😏",
            "Fechado. Hoje a procrastinação perdeu por pontos.",
            "Cumprido. Quase parece que existe um adulto responsável administrando essa agenda.",
            "Boa. Pode aproveitar os próximos cinco minutos se sentindo extremamente organizado.",
        ])

    # Cadastro de prova / mensagens acadêmicas.
    if text.startswith("📝 ") and ("cadastrada" in text or "Registrado" in text):
        return text + " " + _pick([
            "Agora falta só a pequena etapa opcional chamada estudar. 😌",
            "Data salva. Fingir que não sabia ficou oficialmente indisponível.",
            "Pronto. A prova já está na agenda; o conhecimento, infelizmente, ainda exige instalação manual. 😏",
            "Registrada. Vou avisar com antecedência suficiente para o pânico ser uma escolha, não uma necessidade.",
        ])

    # Avisos de prova gerados pela camada acadêmica.
    if "Prova de" in text and any(x in text.lower() for x in ("7 dias", "3 dias", "amanhã", "amanha", "é hoje", "e hoje", "1 hora")):
        if "7 dias" in text:
            return text + " " + _pick([
                "Uma semana. Tempo suficiente para estudar com calma ou para passar seis dias dizendo que ainda está cedo. 😏",
                "Sete dias de vantagem. Vamos observar com interesse científico quando você decide começar.",
                "Ainda está longe o bastante para não entrar em pânico e perto o bastante para não ignorar.",
            ])
        if "3 dias" in text:
            return text + " " + _pick([
                "Três dias. A fase 'depois eu vejo isso' está oficialmente encerrando expediente.",
                "Ainda dá para estudar direito. Também dá para entrar em negação, mas eu recomendo menos a segunda opção. 😌",
                "72 horas. O prazo ainda é civilizado; não precisa transformar isso em esporte radical.",
            ])
        if "amanh" in text.lower():
            return text + " " + _pick([
                "É amanhã. Hoje seria um excelente dia para descobrir se o conteúdo também sabe da prova. 😏",
                "Véspera chegou. Respira, revisa e evita a tradicional tentativa de aprender o semestre inteiro às 02:17.",
                "Amanhã. Neste ponto, organização vale mais que heroísmo acadêmico de madrugada.",
            ])
        if "hoje" in text.lower():
            return text + " " + _pick([
                "Chegou o grande dia. Agora não adianta negociar com o calendário; ele é surpreendentemente inflexível.",
                "É hoje. Conhecimento carregado ou não, a atualização vai para produção. 😌",
                "Boa prova. E sim, eu avisei antes várias vezes, então minha consciência administrativa está limpa. 😏",
            ])

    return text


def install():
    # Cada módulo importou send_message diretamente; por isso substituímos a referência
    # local de ambos, sem alterar telegram_api globalmente.
    q_original = quality_patch.send_message
    a_original = academic_intelligence.send_message

    async def q_send(token, chat_id, text, reply_markup=None):
        return await q_original(token, chat_id, _rewrite(text), reply_markup=reply_markup)

    async def a_send(token, chat_id, text, reply_markup=None):
        return await a_original(token, chat_id, _rewrite(text), reply_markup=reply_markup)

    quality_patch.send_message = q_send
    academic_intelligence.send_message = a_send
