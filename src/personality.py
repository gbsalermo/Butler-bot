import random
from enum import Enum
from datetime import datetime


class Tone(str, Enum):
    NEUTRO = "neutro"
    LEVE = "leve"
    SARCASTICO = "sarcastico"
    CUIDADOSO = "cuidadoso"


_RESPONSES: dict[str, dict[Tone, list[str]]] = {
    "task_reminder": {
        Tone.NEUTRO: ["Chefe, tem uma pendência chamando."],
        Tone.LEVE: ["Chefe, isso aqui está na hora."],
        Tone.SARCASTICO: [
            "Chefe... tenho más notícias: isso não se resolveu sozinho.",
            "Olha quem voltou para cobrar presença: sua responsabilidade.",
            "Eu conferi. Ignorar ainda não conclui tarefa automaticamente.",
        ],
        Tone.CUIDADOSO: ["Só um lembrete, chefe. Quando der, cuide disso."],
    },
    "class_reminder": {
        Tone.NEUTRO: ["Aula chegando, chefe."],
        Tone.LEVE: ["Hora de organizar as coisas para a aula."],
        Tone.SARCASTICO: [
            "Chefe, a faculdade voltou a exigir sua presença física.",
            "Aula chegando. Infelizmente presença por telepatia ainda não vale.",
        ],
        Tone.CUIDADOSO: ["A aula está chegando. Se organize no seu ritmo."],
    },
    "routine_reminder": {
        Tone.NEUTRO: ["Hora de cuidar disso, chefe."],
        Tone.LEVE: ["Manutenção básica do ser humano, chefe."],
        Tone.SARCASTICO: [
            "Chefe, seu corpo abriu um chamado de manutenção.",
            "Mais uma obrigação básica de possuir um corpo humano. Vamos lá.",
        ],
        Tone.CUIDADOSO: ["Um cuidado pequeno agora já ajuda."],
    },
    "done": {
        Tone.NEUTRO: ["Feito. Registrado."],
        Tone.LEVE: ["Boa. Menos uma coisa ocupando espaço na cabeça."],
        Tone.SARCASTICO: [
            "Olha só. Uma coisa concluída. Estamos perigosamente eficientes.",
            "Feito. Eu sabia que insistência eventualmente funcionava.",
            "Resolvido. Vou fingir que nunca duvidei.",
        ],
        Tone.CUIDADOSO: ["Feito. Já é uma coisa a menos para carregar hoje."],
    },
    "snooze": {
        Tone.NEUTRO: ["Certo. Eu volto depois."],
        Tone.LEVE: ["Tudo bem. Vou te dar esse tempo."],
        Tone.SARCASTICO: [
            "Adiado. A responsabilidade ganhou alguns minutos de liberdade.",
            "Certo, chefe. Compramos mais alguns minutos. Use com sabedoria.",
        ],
        Tone.CUIDADOSO: ["Tudo bem. Eu te lembro de novo mais tarde."],
    },
    "routine_done": {
        Tone.NEUTRO: ["Rotina registrada."],
        Tone.LEVE: ["Boa. Constância é esse tipo de coisa pequena mesmo."],
        Tone.SARCASTICO: [
            "Registrado. Veja só, cuidando de si sem eu precisar abrir sindicância.",
            "Mais uma cumprida. O sistema permanece surpreendentemente funcional.",
        ],
        Tone.CUIDADOSO: ["Registrado. Bom ter cuidado de você hoje."],
    },
    "goal_progress": {
        Tone.NEUTRO: ["Progresso registrado."],
        Tone.LEVE: ["Boa. Um pouco hoje ainda conta."],
        Tone.SARCASTICO: [
            "Progresso registrado. Quem diria: números indo na direção certa.",
            "Anotado. Devagar e sempre continua sendo irritantemente eficaz.",
        ],
        Tone.CUIDADOSO: ["Anotado. O importante é continuar avançando sem se esmagar por isso."],
    },
    "wake": {
        Tone.NEUTRO: ["Estou aqui. O que precisamos organizar?"],
        Tone.LEVE: ["Fala daí, chefe. O que pegou?"],
        Tone.SARCASTICO: [
            "Fala daí, chefe. O que aconteceu dessa vez?",
            "Chamou? Certo. Vamos ver o tamanho do estrago.",
            "Estou aqui. Tente me dizer que não é uma emergência criada por procrastinação.",
        ],
        Tone.CUIDADOSO: ["Estou aqui, chefe. Me diga do que precisa."],
    },
    "dayoff": {
        Tone.CUIDADOSO: [
            "Certo, chefe. Hoje eu cuido do silêncio. Me chama se precisar.",
            "Entendido. Hoje não tem cobrança. Eu fico por aqui, quieto.",
        ],
    },
    "greeting": {
        Tone.NEUTRO: ["Fala, chefe."],
        Tone.LEVE: ["Fala daí, chefe. Tudo certo?"],
        Tone.SARCASTICO: ["Fala daí, chefe. Já começou a confusão ou ainda dá tempo?"],
        Tone.CUIDADOSO: ["Oi, chefe. Estou por aqui."],
    },
    "thanks": {
        Tone.NEUTRO: ["À disposição."],
        Tone.LEVE: ["É para isso que me pagam. Quer dizer... enfim."],
        Tone.SARCASTICO: ["Disponha. Meu salário continua rigorosamente em zero."],
        Tone.CUIDADOSO: ["Sempre que precisar."],
    },
}


def choose(event: str, tone: Tone = Tone.LEVE) -> str:
    event_map = _RESPONSES.get(event, {})
    choices = event_map.get(tone) or event_map.get(Tone.LEVE) or event_map.get(Tone.NEUTRO) or [""]
    return random.choice(choices)


def everyday_tone(*, sensitive: bool = False, sarcasm: bool = True) -> Tone:
    if sensitive:
        return Tone.CUIDADOSO
    if sarcasm and random.random() < 0.48:
        return Tone.SARCASTICO
    return Tone.LEVE


def day_flavor() -> str | None:
    # Pequena característica recorrente do personagem: Butler não gosta de terça-feira.
    if datetime.now().weekday() == 1:
        return "Terça-feira. Você sabe o que penso sobre isso."
    return None
