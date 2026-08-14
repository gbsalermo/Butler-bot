import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

WEEKDAYS = {"segunda":0,"segunda-feira":0,"seg":0,"terca":1,"terça":1,"terça-feira":1,"ter":1,"quarta":2,"quarta-feira":2,"qua":2,"quinta":3,"quinta-feira":3,"qui":3,"sexta":4,"sexta-feira":4,"sex":4,"sabado":5,"sábado":5,"sab":5,"domingo":6,"dom":6}

@dataclass
class Intent:
    name: str
    confidence: float
    data: dict = field(default_factory=dict)
    reason: str | None = None

def normalize(text: str) -> str:
    value=unicodedata.normalize("NFKD",(text or "").lower()); value="".join(ch for ch in value if not unicodedata.combining(ch)); return re.sub(r"\s+"," ",value).strip()
def _strip_butler(text: str) -> str: return re.sub(r"^\s*butler[,!:\-]?\s*","",text or "",flags=re.I).strip()

def parse_time(text: str) -> str | None:
    n=normalize(text)
    for pattern in (r"(?:as|pelas?|por volta das?)\s*(\d{1,2})(?:[:h](\d{2}))?\s*h?\b",r"\b(\d{1,2}):(\d{2})\b",r"\b(\d{1,2})h(\d{2})?\b"):
        m=re.search(pattern,n)
        if m:
            h,mi=int(m.group(1)),int(m.group(2) or 0)
            if 0<=h<=23 and 0<=mi<=59:return f"{h:02d}:{mi:02d}"
    return None

def parse_date(text: str,today: date|None=None)->date|None:
    today=today or date.today(); n=normalize(text)
    if "depois de amanha" in n:return today+timedelta(days=2)
    if re.search(r"\bamanha\b",n):return today+timedelta(days=1)
    if re.search(r"\bhoje\b",n):return today
    m=re.search(r"daqui a\s+(\d{1,3})\s+dias?",n)
    if m:return today+timedelta(days=int(m.group(1)))
    m=re.search(r"\b(?:dia\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b",n)
    if m:
        d,mo=int(m.group(1)),int(m.group(2)); y=int(m.group(3)) if m.group(3) else today.year
        if y<100:y+=2000
        try:
            candidate=date(y,mo,d)
            if not m.group(3) and candidate<today:candidate=date(y+1,mo,d)
            return candidate
        except ValueError:return None
    m=re.search(r"\bdia\s+(\d{1,2})\b",n)
    if m:
        try:
            candidate=date(today.year,today.month,int(m.group(1)))
            if candidate<today:
                mo,y=today.month+1,today.year
                if mo==13:mo,y=1,y+1
                candidate=date(y,mo,int(m.group(1)))
            return candidate
        except ValueError:pass
    for label,weekday in WEEKDAYS.items():
        if re.search(rf"\b{re.escape(normalize(label))}\b",n):
            delta=(weekday-today.weekday())%7
            if delta==0 and any(x in n for x in ("proxima","proximo")):delta=7
            return today+timedelta(days=delta)
    return None

def _remove_temporal(text:str)->str:
    s=text
    for pattern in (r"\b(?:hoje|amanhã|amanha|depois de amanhã|depois de amanha)\b",r"\bdaqui a\s+\d+\s+dias?\b",r"\b(?:próxima|proxima|próximo|proximo)?\s*(?:segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)(?:-feira)?\b",r"\b(?:dia\s+)?\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",r"\bdia\s+\d{1,2}\b",r"(?:às|as|pelas?|por volta das?)\s*\d{1,2}(?:[:h]\d{2})?\s*h?\b",r"\b\d{1,2}:\d{2}\b|\b\d{1,2}h(?:\d{2})?\b"):
        s=re.sub(pattern,"",s,flags=re.I)
    return " ".join(s.split()).strip(" ,.-")
def _clean_title(text:str,intent:str)->str:
    s=_remove_temporal(_strip_butler(text))
    patterns=[r"^(?:eu\s+)?tenho\s+",r"^(?:eu\s+)?vou\s+(?:ter|ao|à|a|no|na)\s+",r"^(?:marca|marcar|anota|anotar)\s+(?:um\s+)?(?:compromisso\s+)?(?:de|para|com)?\s*"] if intent=="appointment_create" else [r"^(?:me\s+)?lembra(?:-me)?\s+de\s+",r"^(?:eu\s+)?preciso\s+(?:de\s+)?",r"^(?:eu\s+)?tenho\s+que\s+",r"^(?:anota|anotar|adiciona|adicionar)\s+(?:uma\s+)?tarefa\s+(?:de|para)?\s*"]
    for p in patterns:s=re.sub(p,"",s,flags=re.I)
    return _remove_temporal(s).strip(" ,.-")

def interpret(text:str,today:date|None=None)->Intent|None:
    raw=_strip_butler(text or ""); n=normalize(raw)
    if not n:return None

    grocery_question = any(x in n for x in ("o que falta em casa","o que ta faltando em casa","o que esta faltando em casa","quais itens faltam")) or bool(re.match(r"^(?:mostra|mostrar|lista|listar)\s+(?:a\s+)?(?:lista\s+)?(?:de mercado|da feira|de compras)",n))
    if grocery_question:return Intent("grocery_query",.98)
    if re.search(r"\b(o que|que que|como esta|minha agenda|tenho algo|tenho o que|quais compromissos)\b",n) and any(x in n for x in ("hoje","amanha","depois de amanha","daqui a","segunda","terca","quarta","quinta","sexta","sabado","domingo","agenda","proxima semana")):
        target=parse_date(raw,today)
        if "proximos 7" in n or "proxima semana" in n:return Intent("agenda_range",.95,{"days":7})
        return Intent("agenda_query",.94 if target else .72,{"date":target})
    if any(x in n for x in ("o que ficou pendente","quais pendencias","tarefas atrasadas","o que esta atrasado")):return Intent("overdue_query",.98)
    if any(x in n for x in ("quanto gastei","relatorio de gastos","relatorio financeiro","como estao minhas financas","quanto sobrou","quanto tenho guardado","dinheiro guardado")):return Intent("finance_report",.97)

    m=re.match(r"^(?:comprei|ja comprei|peguei)\s+(.+)$",n)
    if m:return Intent("grocery_bought",.9,{"target":m.group(1).strip()})
    if re.match(r"^(?:ta faltando|esta faltando|falta|faltam)\b",n) or any(x in n for x in ("na lista de mercado","na lista da feira","na lista de compras")):
        cleaned=re.sub(r"^(?:ta faltando|está faltando|esta faltando|falta|faltam|adiciona|adicionar|coloca|colocar|bota|botar|anota|anotar)\s+","",raw,flags=re.I)
        cleaned=re.sub(r"\s+(?:na|pra|para a)\s+lista\s+(?:de mercado|da feira|de compras).*$","",cleaned,flags=re.I)
        return Intent("grocery_add",.97,{"items":[x.strip() for x in re.split(r",|\s+e\s+",cleaned) if x.strip()]})

    if any(x in n for x in ("nao vou treinar","nao consigo treinar","nao consigo ir treinar","nao vai dar pra treinar","nao vai dar para treinar","nao vou pra academia","nao vou para academia","vou faltar o treino")):
        m=re.search(r"\bporque\s+(.+)$",raw,flags=re.I); return Intent("workout_skip",.98,{"reason":m.group(1).strip() if m else None})
    if any(x in n for x in ("vou me atrasar","vou chegar atrasado","estou atrasado","to atrasado")):
        s=re.sub(r"^.*?(?:vou me atrasar|vou chegar atrasado|estou atrasado|tô atrasado|to atrasado)\s*(?:para|pro|pra|no|na)?\s*","",raw,flags=re.I).strip(); return Intent("late_notice",.95,{"target":s or None})
    m=re.search(r"\b(?:ja\s+)?(?:fiz|terminei|conclui|resolvi)\s+(.+)$",n)
    if m:return Intent("task_complete",.9,{"target":m.group(1).strip()})

    m=re.search(r"\b(?:gastei|paguei|saiu)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais?)?\s*(?:com|em|de)?\s*(.*)$",n)
    if m:return Intent("finance_add",.96,{"kind":"saida","amount":float(m.group(1).replace(",",".")),"description":m.group(2).strip() or None})
    m=re.search(r"\b(?:recebi|entrou|ganhei)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais?)?\s*(?:de|da|do)?\s*(.*)$",n)
    if m:return Intent("finance_add",.96,{"kind":"entrada","amount":float(m.group(1).replace(",",".")),"description":m.group(2).strip() or None})

    appointment_markers=("tenho consulta","tenho dentista","tenho medico","tenho reuniao","tenho prova","vou ao medico","vou no dentista","vou ter reuniao","marca compromisso","marcar compromisso","anota compromisso","anotar compromisso")
    appointment_nouns=("dentista","consulta","medico","reuniao","prova","entrevista","consulta medica")
    d,t=parse_date(raw,today),parse_time(raw)
    if any(x in n for x in appointment_markers) or (d and t and any(x in n for x in appointment_nouns)):
        title=_clean_title(raw,"appointment_create"); return Intent("appointment_create",.96 if (d and t and title) else .82,{"title":title,"date":d,"time":t})

    task_markers=("me lembra de","lembra-me de","preciso ","tenho que ","anota uma tarefa","anotar uma tarefa","adiciona uma tarefa")
    if any(x in n for x in task_markers):
        title=_clean_title(raw,"task_create"); reminder_request="lembra" in n
        return Intent("task_create",.95 if title else .7,{"title":title,"date":d,"time":t,"reminder_request":reminder_request})
    return None

def validate_future(target_date:date|None,target_time:str|None,now:datetime|None=None)->tuple[bool,str|None]:
    now=now or datetime.now()
    if target_date is None:return True,None
    if target_date<now.date():return False,"Essa data já passou. Nem eu consigo organizar viagem no tempo."
    if target_date==now.date() and target_time:
        h,m=map(int,target_time.split(":")); target=datetime.combine(target_date,datetime.min.time()).replace(hour=h,minute=m)
        if target<=now:return False,"Esse horário já passou. Posso cobrar responsabilidade; alterar a linha do tempo ainda não."
    return True,None
