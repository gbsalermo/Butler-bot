"""Roteador central de contexto do Butler.

Não executa regra de negócio. Classifica a mensagem para preservar a ordem:
Core > contexto explícito > memória > Library > conversa.
"""
from dataclasses import dataclass

from language_context import normalize_informal, detect_core_domain, conversation_shape
from intent_parser import parse as parse_intent

OPTIONAL_HINTS = {
    "cooking": ("receita","cozinhar","fazer comida","macarrao","massa","carne","frango","arroz","feijao","salada","bolo","doce","moqueca","vatapa","baiao"),
    "games": ("jogo","jogar","pc","playstation","xbox","nintendo","pokemon","fire red","firered"),
    "movies_series": ("filme","serie","episodio","temporada","assistir","personagem"),
    "books": ("livro","ler","leitura","autor","romance","literatura"),
    "culture": ("quem e","quem foi","me fala sobre","me explica"),
}

@dataclass(frozen=True)
class Route:
    domain: str
    tier: str
    shape: str
    confidence: int
    normalized: str
    intent: str = "conversation"
    target: str | None = None
    time_hint: str | None = None


def _contains_hint(n,words,hint):
    h=normalize_informal(hint)
    if not h:return False
    if " " in h:return h in n
    return h in words


def classify(text):
    n=normalize_informal(text)
    shape=conversation_shape(text)
    parsed=parse_intent(text)

    if parsed.domain != "conversation" and parsed.confidence >= 75:
        tier="core" if parsed.domain in {"academic","tasks","appointments","grocery","workout","finance","routine"} else "library"
        return Route(parsed.domain,tier,shape,parsed.confidence,n,parsed.intent,parsed.target,parsed.time_hint)

    core=detect_core_domain(text)
    if core:
        return Route(core,"core",shape,100,n,parsed.intent,parsed.target,parsed.time_hint)

    scores={}; words=set(n.split())
    for domain,hints in OPTIONAL_HINTS.items():
        for hint in hints:
            if _contains_hint(n,words,hint):
                scores[domain]=scores.get(domain,0)+(3 if " " in normalize_informal(hint) else 2)
    if scores:
        domain,score=max(scores.items(),key=lambda x:x[1])
        return Route(domain,"library",shape,min(90,40+score*5),n,parsed.intent,parsed.target,parsed.time_hint)
    return Route("conversation","conversation",shape,20,n,parsed.intent,parsed.target,parsed.time_hint)


def allow_optional(route,domain=None):
    if route.tier=="core":return False
    if domain is None:return True
    return route.domain in (domain,"conversation","culture")
