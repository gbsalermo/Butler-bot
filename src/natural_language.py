import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

WEEKDAYS = {
    "segunda": 0, "segunda-feira": 0, "seg": 0,
    "terca": 1, "terça": 1, "terça-feira": 1, "ter": 1,
    "quarta": 2, "quarta-feira": 2, "qua": 2,
    "quinta": 3, "quinta-feira": 3, "qui": 3,
    "sexta": 4, "sexta-feira": 4, "sex": 4,
    "sabado": 5, "sábado": 5, "sab": 5,
    "domingo": 6, "dom": 6,
}

@dataclass
class Intent:
    name: str
    confidence: float
    data: dict = field(default_factory=dict)
    reason: str | None = None


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _strip_butler(text: str) -> str:
    text = re.sub(r"^\s*(butler[,!:\-]?\s*)", "", text, flags=re.I)
    return text.strip()


def parse_time(text: str) -> str | None:
    n = normalize(text)
    patterns = [
        r"(?:as|às|pelas?|por volta das?)\s*(\d{1,2})(?:[:h](\d{2}))?\s*h?\b",
        r"\b(\d{1,2}):(\d{2})\b",
        r"\b(\d{1,2})h(\d{2})?\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, n)
        if not m:
            continue
        hour = int(m.group(1)); minute = int(m.group(2) or 0)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    return None


def parse_date(text: str, today: date | None = None) -> date | None:
    today = today or date.today()
    n = normalize(text)
    if "depois de amanha" in n:
        return today + timedelta(days=2)
    if re.search(r"\bamanha\b", n):
        return today + timedelta(days=1)
    if re.search(r"\bhoje\b", n):
        return today
    m = re.search(r"daqui a\s+(\d{1,3})\s+dias?", n)
    if m:
        return today + timedelta(days=int(m.group(1)))
    m = re.search(r"\b(?:dia\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", n)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else today.year
        if year < 100: year += 2000
        try:
            candidate = date(year, month, day)
            if not m.group(3) and candidate < today:
                candidate = date(year + 1, month, day)
            return candidate
        except ValueError:
            return None
    m = re.search(r"\bdia\s+(\d{1,2})\b", n)
    if m:
        day = int(m.group(1))
        try:
            candidate = date(today.year, today.month, day)
            if candidate < today:
                month = today.month + 1; year = today.year
                if month == 13: month = 1; year += 1
                candidate = date(year, month, day)
            return candidate
        except ValueError:
            pass
    for label, weekday in WEEKDAYS.items():
        if re.search(rf"\b{re.escape(normalize(label))}\b", n):
            delta = (weekday - today.weekday()) % 7
            if delta == 0 and any(x in n for x in ("proxima", "proximo")):
                delta = 7
            return today + timedelta(days=delta)
    return None


def _remove_temporal(text: str) -> str:
    s = text
    s = re.sub(r"\b(?:hoje|amanhã|amanha|depois de amanhã|depois de amanha)\b", "", s, flags=re.I)
    s = re.sub(r"\bdaqui a\s+\d+\s+dias?\b", "", s, flags=re.I)
    s = re.sub(r"\b(?:segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)(?:-feira)?\b", "", s, flags=re.I)
    s = re.sub(r"\b(?:dia\s+)?\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", "", s, flags=re.I)
    s = re.sub(r"\bdia\s+\d{1,2}\b", "", s, flags=re.I)
    s = re.sub(r"(?:às|as|pelas?|por volta das?)\s*\d{1,2}(?:[:h]\d{2})?\s*h?\b", "", s, flags=re.I)
    s = re.sub(r"\b\d{1,2}:\d{2}\b", "", s)
    s = re.sub(r"\b\d{1,2}h(?:\d{2})?\b", "", s, flags=re.I)
    return " ".join(s.split()).strip(" ,.-")


def _clean_title(text: str, intent: str) -> str:
    s = _strip_butler(text)
    patterns = []
    if intent == "appointment_create":
        patterns = [r"^(?:eu\s+)?tenho\s+", r"^(?:eu\s+)?vou\s+(?:ter|ao|à|a|no|na)\s+", r"^marca(?:r)?\s+(?:um\s+)?compromisso\s+(?:de|para|com)?\s*"]
    elif intent == "task_create":
        patterns = [r"^(?:me\s+)?lembra(?:-me)?\s+de\s+", r"^(?:eu\s+)?preciso\s+(?:de\s+)?", r"^(?:eu\s+)?tenho\s+que\s+", r"^anota(?:r)?\s+(?:uma\s+)?tarefa\s+(?:de|para)?\s*"]
    for p in patterns:
        s = re.sub(p, "", s, flags=re.I)
    s = _remove_temporal(s)
    s = re.sub(r"\b(?:pra|para)\s*$", "", s, flags=re.I)
    return s.strip(" ,.-")


def interpret(text: str, today: date | None = None) -> Intent | None:
    raw = _strip_butler(text or "")
    n = normalize(raw)
    if not n:
        return None

    # Consultas
    if re.search(r"\b(o que|que que|como esta|minha agenda|tenho algo|tenho o que)\b", n) and any(x in n for x in ("hoje", "amanha", "depois de amanha", "daqui a", "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo", "agenda")):
        target = parse_date(raw, today)
        if "proximos 7" in n or "proxima semana" in n:
            return Intent("agenda_range", .95, {"days": 7})
        return Intent("agenda_query", .94 if target else .72, {"date": target})
    if any(x in n for x in ("o que ficou pendente", "quais pendencias", "tarefas atrasadas", "o que esta atrasado")):
        return Intent("overdue_query", .98)
    if any(x in n for x in ("quanto gastei", "relatorio de gastos", "relatorio financeiro", "como estao minhas financas", "quanto sobrou")):
        return Intent("finance_report", .97)

    # Mercado
    if re.match(r"^(?:ta faltando|esta faltando|falta|faltam)\b", n) or any(x in n for x in ("na lista de mercado", "na lista da feira", "na lista de compras")):
        cleaned = re.sub(r"^(?:ta faltando|está faltando|esta faltando|falta|faltam)\s+", "", raw, flags=re.I)
        cleaned = re.sub(r"\s+(?:na lista de mercado|na lista da feira|na lista de compras).*$", "", cleaned, flags=re.I)
        items = [x.strip() for x in re.split(r",|\s+e\s+", cleaned) if x.strip()]
        return Intent("grocery_add", .97, {"items": items})

    # Academia - falta
    if any(x in n for x in ("nao vou treinar", "nao consigo treinar", "nao vou pra academia", "nao vou para academia", "vou faltar o treino")):
        reason = None
        m = re.search(r"\bporque\s+(.+)$", raw, flags=re.I)
        if m: reason = m.group(1).strip()
        return Intent("workout_skip", .98, {"reason": reason})

    # Atraso
    if any(x in n for x in ("vou me atrasar", "vou chegar atrasado", "estou atrasado", "to atrasado")):
        s = re.sub(r"^.*?(?:vou me atrasar|vou chegar atrasado|estou atrasado|tô atrasado|to atrasado)\s*(?:para|pro|pra|no|na)?\s*", "", raw, flags=re.I).strip()
        return Intent("late_notice", .95, {"target": s or None})

    # Conclusão de tarefa
    m = re.match(r"^(?:ja\s+)?(?:fiz|terminei|conclui|resolvi)\s+(.+)$", n)
    if m:
        return Intent("task_complete", .9, {"target": raw[raw.lower().find(m.group(1)):].strip() if m.group(1) in raw.lower() else m.group(1)})

    # Finanças por texto
    m = re.search(r"\b(?:gastei|paguei|saiu)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais?)?\s*(?:com|em|de)?\s*(.*)$", n)
    if m:
        return Intent("finance_add", .96, {"kind": "saida", "amount": float(m.group(1).replace(",", ".")), "description": m.group(2).strip() or None})
    m = re.search(r"\b(?:recebi|entrou|ganhei)\s+(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais?)?\s*(?:de|da|do)?\s*(.*)$", n)
    if m:
        return Intent("finance_add", .96, {"kind": "entrada", "amount": float(m.group(1).replace(",", ".")), "description": m.group(2).strip() or None})

    # Compromissos
    appointment_markers = ("tenho consulta", "tenho dentista", "tenho medico", "tenho médico", "tenho reuniao", "tenho reunião", "tenho prova", "vou ao medico", "vou ao médico", "vou no dentista", "vou ter reuniao", "vou ter reunião")
    if any(normalize(x) in n for x in appointment_markers):
        d, t = parse_date(raw, today), parse_time(raw)
        title = _clean_title(raw, "appointment_create")
        return Intent("appointment_create", .96 if (d and t and title) else .82, {"title": title, "date": d, "time": t})

    # Tarefas / lembretes
    if re.match(r"^(?:me )?lembra(?:-me)? de\b", n) or re.match(r"^(?:eu )?(?:preciso|tenho que)\b", n):
        d, t = parse_date(raw, today), parse_time(raw)
        title = _clean_title(raw, "task_create")
        return Intent("task_create", .95 if title else .7, {"title": title, "date": d, "time": t})

    return None


def validate_future(target_date: date | None, target_time: str | None, now: datetime | None = None) -> tuple[bool, str | None]:
    now = now or datetime.now()
    if target_date is None:
        return True, None
    if target_date < now.date():
        return False, "Essa data já passou. Nem eu consigo organizar viagem no tempo."
    if target_date == now.date() and target_time:
        hour, minute = map(int, target_time.split(":"))
        target = datetime.combine(target_date, datetime.min.time()).replace(hour=hour, minute=minute)
        if target <= now:
            return False, "Esse horário já passou. Posso cobrar responsabilidade; alterar a linha do tempo ainda não."
    return True, None
