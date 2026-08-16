"""Parser estrutural leve: intenção + alvo + pistas temporais.

Não executa ações. Serve para reduzir dependência de frases exatas e alimentar
roteamento, memória curta e sugestões. Validação continua nos módulos do Core.
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
    # Musculação vem antes de ausência acadêmica para "faltar ao treino".
    ("workout_skip","workout",(
        r"(?:nao consigo|nao vou conseguir|nao vou) treinar(?P<target>.*)",
        r"vou faltar (?:o|ao) treino(?P<target>.*)",
    ),94),
    ("workout_query","workout",(
        r"qual (?:e |é )?o? ?treino(?: de)? (?P<target>.+)",
        r"treino de (?P<target>.+)",
        r"o que treino (?P<target>.+)",
    ),82),

    # Acadêmico
    ("academic_absence","academic",(
        r"(?:quero|queria|vou|pretendo|acho que vou) (?:faltar|matar)(?: a| na| em)? (?P<target>.+)",
        r"nao vou (?:pra|para|na) (?:aula de )?(?P<target>.+)",
        r"(?:vou|quero) faltar (?P<target>.+)",
    ),92),
    ("academic_query","academic",(
        r"(?:qual|quais|que) (?:minha|minhas)? ?(?:aula|aulas|materia|materias|disciplina|disciplinas)(?P<target>.*)",
        r"(?:o que|que) tenho.+(?:faculdade|aula|materia)(?P<target>.*)",
        r"(?:tenho|tem) prova(?: de)? (?P<target>.+)",
    ),82),
    ("academic_exam","academic",(
        r"(?:tenho|vai ter|vou ter) prova(?: de)? (?P<target>.+)",
        r"prova de (?P<target>.+)",
    ),82),

    # Tarefas / lembretes
    ("task_reminder","tasks",(
        r"me lembra(?: de)? (?P<target>.+)",
        r"me lembre(?: de)? (?P<target>.+)",
        r"nao posso esquecer(?: de)? (?P<target>.+)",
    ),96),
    ("task_create","tasks",(
        r"(?:tenho|preciso) (?:que|de)? ?fazer (?P<target>.+)",
        r"anota(?: pra mim| para mim)? (?P<target>.+)",
        r"cria(?: uma)? tarefa(?: pra| para)? (?P<target>.+)",
    ),84),
    ("task_complete","tasks",(
        r"(?:ja fiz|terminei|conclui) (?P<target>.+)",
    ),84),

    # Mercado
    ("grocery_add","grocery",(
        r"(?:bota|coloca|adiciona) (?P<target>.+) na lista",
        r"(?:bota|coloca|adiciona) na lista (?P<target>.+)",
        r"preciso comprar (?P<target>.+)",
        r"^comprar (?P<target>.+)",
    ),88),
    ("grocery_query","grocery",(
        r"(?:o que|oq|que) (?:esta|ta) faltando(?: em casa)?(?P<target>.*)",
        r"(?:o que|oq) tem na lista(?P<target>.*)",
    ),82),

    # Compromissos / agenda
    ("appointment_query","appointments",(
        r"(?:o que|que|oq) tenho (?:agendado|marcado)? ?(?P<target>.+)",
        r"(?:minha agenda|agenda) (?P<target>.+)",
    ),82),
    ("appointment_create","appointments",(
        r"(?:marca|marque|agenda|agende) (?P<target>.+)",
        r"tenho (?:dentista|consulta|reuniao|reunião|compromisso) (?P<target>.+)",
    ),84),

    # Finanças
    ("finance_expense","finance",(
        r"gastei (?P<target>.+)",
        r"paguei (?P<target>.+)",
    ),88),
    ("finance_income","finance",(
        r"recebi (?P<target>.+)",
        r"entrou (?P<target>.+)",
    ),86),
    ("finance_query","finance",(
        r"quanto (?:gastei|entrou|saiu)(?P<target>.*)",
        r"(?:saldo|gastos) (?P<target>.+)",
    ),84),

    # Rotina / metas
    ("routine_create","routine",(
        r"(?:cria|monta|quero) (?:uma )?rotina(?: de| para)? (?P<target>.+)",
        r"quero (?:fazer|ter) (?P<target>.+) todo dia",
        r"quero (?P<target>.+) todo dia",
    ),82),
    ("routine_query","routine",(
        r"(?:qual|quais) (?:minha|minhas)? ?rotinas?(?P<target>.*)",
        r"como (?:esta|ta) minha rotina(?P<target>.*)",
    ),80),

    # Library
    ("cooking_request","cooking",(
        r"(?:receita de|como fazer|como preparo|queria fazer|quero fazer) (?P<target>.+)",
        r"(?:o que|oq) posso fazer com (?P<target>.+)",
        r"sobrou (?P<target>.+)",
    ),82),
    ("recommend_game","games",(
        r"(?:me )?(?:indica|recomenda|sugere).*(?:jogo|game)(?P<target>.*)",
        r"quero (?:um )?jogo (?P<target>.+)",
    ),78),
    ("recommend_book","books",(
        r"(?:me )?(?:indica|recomenda|sugere).*(?:livro|leitura)(?P<target>.*)",
        r"quero (?:um )?livro (?P<target>.+)",
    ),78),
    ("recommend_screen","movies_series",(
        r"(?:me )?(?:indica|recomenda|sugere).*(?:filme|serie)(?P<target>.*)",
        r"quero (?:um|uma) (?:filme|serie) (?P<target>.+)",
    ),78),
)

def _time_hint(n):
    for day in DAY_WORDS:
        if re.search(r"\b"+day+r"\b",n):return day
    m=re.search(r"\b(?:as\s+)?(\d{1,2})(?::(\d{2}))?\s*h\b",n)
    if m:return m.group(0).strip()
    m=re.search(r"daqui a \d+ (?:dias|semanas|meses)",n)
    if m:return m.group(0)
    m=re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",n)
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
