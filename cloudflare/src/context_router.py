"""Roteador central de contexto do Butler.

Não executa regra de negócio. Classifica a mensagem para que o dispatcher preserve
uma ordem única: Core > contexto explícito > memória > Library > conversa.
"""
from dataclasses import dataclass

from language_context import normalize_informal, detect_core_domain, conversation_shape

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


def classify(text):
    n=normalize_informal(text)
    shape=conversation_shape(text)
    core=detect_core_domain(text)
    if core:
        return Route(core,"core",shape,100,n)
    scores={}
    for domain,hints in OPTIONAL_HINTS.items():
        for hint in hints:
            h=normalize_informal(hint)
            if h and (h in n or (" " not in h and h in set(n.split()))):
                scores[domain]=scores.get(domain,0)+(3 if " " in h else 2)
    if scores:
        domain,score=max(scores.items(),key=lambda x:x[1])
        return Route(domain,"library",shape,min(90,40+score*5),n)
    return Route("conversation","conversation",shape,20,n)


def allow_optional(route, domain=None):
    if route.tier=="core":return False
    if domain is None:return True
    return route.domain in (domain,"conversation","culture")
