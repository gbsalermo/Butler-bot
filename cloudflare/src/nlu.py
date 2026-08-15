import re
import unicodedata
from datetime import date, datetime, timedelta

WEEKDAYS={"segunda":0,"segunda-feira":0,"seg":0,"terca":1,"terça":1,"terça-feira":1,"ter":1,"quarta":2,"quarta-feira":2,"qua":2,"quinta":3,"quinta-feira":3,"qui":3,"sexta":4,"sexta-feira":4,"sex":4,"sabado":5,"sábado":5,"sab":5,"domingo":6,"dom":6}
GROCERY_TERMS={"arroz","feijao","feijão","acucar","açúcar","sal","cafe","café","leite","pao","pão","ovo","ovos","frango","carne","peixe","macarrao","macarrão","farinha","oleo","óleo","azeite","manteiga","margarina","queijo","presunto","iogurte","agua","água","suco","refrigerante","biscoito","bolacha","fruta","frutas","banana","maca","maçã","laranja","tomate","cebola","alho","batata","cenoura","alface","verdura","verduras","legume","legumes","detergente","sabao","sabão","sabonete","shampoo","condicionador","papel higienico","papel higiênico","desodorante","pasta de dente","creme dental","esponja","agua sanitaria","água sanitária","amaciante"}

def normalize(text):
    value=unicodedata.normalize("NFKD",(text or "").lower());value="".join(ch for ch in value if not unicodedata.combining(ch));return re.sub(r"\s+"," ",value).strip()
def strip_butler(text):return re.sub(r"^\s*butler[,!:\-]?\s*","",text or "",flags=re.I).strip()
def parse_time(text):
    n=normalize(text)
    for p in (r"(?:as|pelas?|por volta das?)\s*(\d{1,2})(?:[:h](\d{2}))?\s*h?\b",r"\b(\d{1,2}):(\d{2})\b",r"\b(\d{1,2})h(\d{2})?\b"):
        m=re.search(p,n)
        if m:
            h,mi=int(m.group(1)),int(m.group(2) or 0)
            if 0<=h<=23 and 0<=mi<=59:return f"{h:02d}:{mi:02d}"
    return None
def parse_date(text,today=None):
    today=today or date.today();n=normalize(text)
    if "depois de amanha" in n:return today+timedelta(days=2)
    if re.search(r"\bamanha\b",n):return today+timedelta(days=1)
    if re.search(r"\bhoje\b",n):return today
    m=re.search(r"daqui a\s+(\d{1,3})\s+dias?",n)
    if m:return today+timedelta(days=int(m.group(1)))
    m=re.search(r"\b(?:dia\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b",n)
    if m:
        d,mo=int(m.group(1)),int(m.group(2));y=int(m.group(3)) if m.group(3) else today.year
        if y<100:y+=2000
        try:
            candidate=date(y,mo,d)
            if not m.group(3) and candidate<today:candidate=date(y+1,mo,d)
            return candidate
        except ValueError:return None
    for label,weekday in WEEKDAYS.items():
        if re.search(rf"\b{re.escape(normalize(label))}\b",n):
            delta=(weekday-today.weekday())%7
            if delta==0 and any(x in n for x in ("proxima","proximo")):delta=7
            return today+timedelta(days=delta)
    return None
def remove_temporal(text):
    s=text
    for p in (r"\b(?:hoje|amanhã|amanha|depois de amanhã|depois de amanha)\b",r"\bdaqui a\s+\d+\s+dias?\b",r"\b(?:próxima|proxima|próximo|proximo)?\s*(?:segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)(?:-feira)?\b",r"\b(?:dia\s+)?\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",r"(?:às|as|pelas?|por volta das?)\s*\d{1,2}(?:[:h]\d{2})?\s*h?\b",r"\b\d{1,2}:\d{2}\b|\b\d{1,2}h(?:\d{2})?\b"):
        s=re.sub(p,"",s,flags=re.I)
    return " ".join(s.split()).strip(" ,.-")
def clean_title(text,kind):
    s=remove_temporal(strip_butler(text));patterns=[r"^(?:eu\s+)?tenho\s+",r"^(?:eu\s+)?vou\s+(?:ter|ao|à|a|no|na)\s+",r"^(?:marca|marcar|anota|anotar)\s+(?:um\s+)?(?:compromisso\s+)?(?:de|para|com)?\s*"] if kind=="compromisso" else [r"^(?:me\s+)?lembra(?:-me)?\s+de\s+",r"^(?:eu\s+)?preciso\s+(?:de\s+)?",r"^(?:eu\s+)?tenho\s+que\s+",r"^(?:anota|anotar|adiciona|adicionar)\s+(?:uma\s+)?tarefa\s+(?:de|para)?\s*"]
    for p in patterns:s=re.sub(p,"",s,flags=re.I)
    return remove_temporal(s).strip(" ,.-")
def interpret(text,today=None):
    raw=strip_butler(text);n=normalize(raw);today=today or date.today()
    if not n:return None
    if any(x in n for x in ("o que falta em casa","o que ta faltando em casa","o que esta faltando em casa","quais itens faltam")) or re.match(r"^(?:mostra|lista|listar).*(?:mercado|feira|compras)",n):return("grocery_query",{})
    if any(x in n for x in ("o que ficou pendente","quais pendencias","tarefas atrasadas","o que esta atrasado")):return("overdue_query",{})
    if any(x in n for x in ("quanto gastei","relatorio de gastos","relatorio financeiro","como estao minhas financas","quanto sobrou","quanto tenho guardado","dinheiro guardado")):return("finance_report",{})
    if any(x in n for x in ("proxima semana","proximos 7 dias")):return("agenda_range",{"days":7})
    if re.search(r"\b(o que|como esta|minha agenda|tenho o que|quais compromissos)\b",n) and (parse_date(raw,today) or "agenda" in n):return("agenda_query",{"date":parse_date(raw,today)})
    m=re.match(r"^(?:comprei|ja comprei|peguei)\s+(.+)$",n)
    if m:return("grocery_bought",{"target":m.group(1).strip()})
    if re.match(r"^(?:ta faltando|esta faltando|falta|faltam)\b",n) or any(x in n for x in ("na lista de mercado","na lista da feira","na lista de compras")):
        cleaned=re.sub(r"^(?:ta faltando|está faltando|esta faltando|falta|faltam|adiciona|adicionar|coloca|colocar|bota|botar|anota|anotar)\s+","",raw,flags=re.I);cleaned=re.sub(r"\s+(?:na|pra|para a)\s+lista\s+(?:de mercado|da feira|de compras).*$","",cleaned,flags=re.I);return("grocery_add",{"items":[x.strip() for x in re.split(r",|\s+e\s+",cleaned) if x.strip()]})
    m=re.match(r"^(?:eu\s+)?(?:preciso|tenho que)\s+comprar\s+(.+)$",n)
    if m:
        parts=[x.strip() for x in re.split(r",|\s+e\s+",remove_temporal(m.group(1))) if x.strip()];known={normalize(x) for x in GROCERY_TERMS}
        if parts and all(normalize(x) in known for x in parts):return("grocery_add",{"items":parts})
    if any(x in n for x in ("nao vou treinar","nao consigo treinar","nao vai dar pra treinar","nao vai dar para treinar","nao vou pra academia","nao vou para academia")):
        m=re.search(r"\bporque\s+(.+)$",raw,flags=re.I);return("workout_skip",{"reason":m.group(1).strip() if m else None})
    if any(x in n for x in ("vou me atrasar","vou chegar atrasado","estou atrasado","to atrasado")):
        s=re.sub(r"^.*?(?:vou me atrasar|vou chegar atrasado|estou atrasado|to atrasado)\s*(?:para|pro|pra|no|na)?\s*","",raw,flags=re.I).strip();return("late_notice",{"target":s or None})
    m=re.search(r"\b(?:ja\s+)?(?:fiz|terminei|conclui|resolvi)\s+(.+)$",n)
    if m:return("task_complete",{"target":m.group(1).strip()})
    m=re.search(r"\b(?:gastei|paguei|saiu)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais?)?\s*(?:com|em|de)?\s*(.*)$",n)
    if m:return("finance_add",{"kind":"saida","amount":float(m.group(1).replace(",",".")),"description":m.group(2).strip() or None})
    m=re.search(r"\b(?:recebi|entrou|ganhei)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais?)?\s*(?:de|da|do)?\s*(.*)$",n)
    if m:return("finance_add",{"kind":"entrada","amount":float(m.group(1).replace(",",".")),"description":m.group(2).strip() or None})
    d,t=parse_date(raw,today),parse_time(raw)
    # Lembrete em ordem natural: "me lembra hoje às 22:33 de que eu tô bem".
    m=re.match(r"^(?:me\s+)?(?:lembra|lembre)(?:-me)?\b(.*)$",raw,flags=re.I)
    if m:
        body=m.group(1).strip();title=None
        dm=re.search(r"\bde\s+(?:que\s+)?(.+)$",body,flags=re.I)
        if dm:title=remove_temporal(dm.group(1)).strip(" ,.-")
        if not title:title=clean_title(raw,"tarefa")
        return("task_create",{"title":title or "lembrete","date":d,"time":t,"reminder_request":True})
    if any(x in n for x in ("tenho consulta","tenho dentista","tenho medico","tenho reuniao","tenho prova","vou ao medico","vou no dentista","vou ter reuniao","marca compromisso","anota compromisso")) or (d and t and any(x in n for x in ("dentista","consulta","medico","reuniao","prova","entrevista"))):return("appointment_create",{"title":clean_title(raw,"compromisso"),"date":d,"time":t})
    if any(x in n for x in ("me lembra de","lembra-me de","preciso ","tenho que ","anota uma tarefa","adiciona uma tarefa")):return("task_create",{"title":clean_title(raw,"tarefa"),"date":d,"time":t,"reminder_request":"lembra" in n})
    return None

def validate_future(target_date,target_time,now):
    if target_date is None:return True,None
    if target_date<now.date():return False,"Essa data já passou. Nem eu consigo organizar viagem no tempo."
    if target_date==now.date() and target_time:
        h,m=map(int,target_time.split(":"));target=datetime.combine(target_date,datetime.min.time()).replace(hour=h,minute=m)
        if target<=now:return False,"Esse horário já passou. Posso cobrar responsabilidade; alterar a linha do tempo ainda não."
    return True,None
