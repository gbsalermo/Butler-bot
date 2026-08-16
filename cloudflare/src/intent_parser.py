"""Parser estrutural leve: intenção + alvo + pistas temporais.

Não executa ações. Serve para reduzir dependência de frases exatas e alimentar
roteamento, memória curta e sugestões.
"""
import re
from dataclasses import dataclass, field
from language_context import normalize_informal

@dataclass(frozen=True)
class ParsedIntent:
    intent: str
    domain: str
    target: str | None = None
    time_hint: str | None = None
    confidence: int = 0
    features: dict = field(default_factory=dict)

DAY_WORDS=("hoje","amanha","segunda","terca","quarta","quinta","sexta","sabado","domingo")

PATTERNS=(
    ("academic_absence","academic",(r"(?:quero|queria|vou|pretendo|acho que vou) (?:faltar|matar)(?: a| na)? (?P<target>.+)",r"nao vou (?:pra|para) (?:aula de )?(?P<target>.+)"),90),
    ("academic_query","academic",(r"(?:qual|quais|que) (?:aula|materia).+",r"(?:o que|que) tenho.+(?:faculdade|aula)"),80),
    ("task_reminder","tasks",(r"me lembra(?: de)? (?P<target>.+)",r"me lembre(?: de)? (?P<target>.+)"),95),
    ("task_create","tasks",(r"(?:tenho|preciso) (?:que|de) fazer (?P<target>.+)",r"anota(?: pra mim)? (?P<target>.+)"),80),
    ("grocery_add","grocery",(r"(?:bota|coloca|adiciona) (?P<target>.+) na lista",r"preciso comprar (?P<target>.+)"),85),
    ("appointment_query","appointments",(r"(?:o que|que|oq) tenho (?:agendado )?(?P<target>.+)",),80),
    ("workout_query","workout",(r"qual (?:e |é )?o? ?treino(?: de)? (?P<target>.+)",r"treino de (?P<target>.+)"),80),
    ("finance_expense","finance",(r"gastei (?P<target>.+)",),85),
    ("cooking_request","cooking",(r"(?:receita de|como fazer|queria fazer|quero fazer) (?P<target>.+)",),80),
    ("recommend_game","games",(r"(?:me )?(?:indica|recomenda).*(?:jogo|game)(?P<target>.*)",),75),
    ("recommend_book","books",(r"(?:me )?(?:indica|recomenda).*(?:livro|leitura)(?P<target>.*)",),75),
    ("recommend_screen","movies_series",(r"(?:me )?(?:indica|recomenda).*(?:filme|serie)(?P<target>.*)",),75),
)

def _time_hint(n):
    for day in DAY_WORDS:
        if re.search(r"\b"+day+r"\b",n):return day
    m=re.search(r"\b(?:as|às)?\s*(\d{1,2})(?::(\d{2}))?\s*h?\b",n)
    if m:return m.group(0).strip()
    m=re.search(r"daqui a \d+ (?:dias|semanas|meses)",n)
    return m.group(0) if m else None

def parse(text):
    n=normalize_informal(text)
    for intent,domain,patterns,confidence in PATTERNS:
        for pattern in patterns:
            m=re.search(pattern,n)
            if not m:continue
            target=(m.groupdict().get("target") or "").strip(" .,-") or None
            return ParsedIntent(intent,domain,target,_time_hint(n),confidence,{"normalized":n})
    return ParsedIntent("conversation","conversation",None,_time_hint(n),20,{"normalized":n})
