import re
import unicodedata

from knowledge.portuguese_conversation import INFORMAL_EQUIVALENTS, CORE_DOMAIN_TERMS, CORE_PATTERNS


def _strip_accents(text):
    value=unicodedata.normalize("NFKD",text or "")
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalize_informal(text):
    raw=_strip_accents((text or "").lower())
    raw=re.sub(r"[^a-z0-9 ]+"," ",raw)
    tokens=[]
    for token in raw.split():
        tokens.extend(INFORMAL_EQUIVALENTS.get(token,token).split())
    return re.sub(r"\s+"," "," ".join(tokens)).strip()


def detect_core_domain(text):
    n=normalize_informal(text)
    scores={}
    for domain,patterns in CORE_PATTERNS.items():
        for p in patterns:
            pn=normalize_informal(p)
            if pn and pn in n:scores[domain]=scores.get(domain,0)+4
    words=set(n.split())
    for domain,terms in CORE_DOMAIN_TERMS.items():
        for term in terms:
            tn=normalize_informal(term)
            if " " in tn:
                if tn in n:scores[domain]=scores.get(domain,0)+2
            elif tn in words:scores[domain]=scores.get(domain,0)+1
    if not scores:return None
    domain,score=max(scores.items(),key=lambda x:x[1])
    return domain if score>=2 else None


def is_protected_core_message(text):
    return detect_core_domain(text) is not None


def conversation_shape(text):
    n=normalize_informal(text)
    if "?" in (text or ""):return "question"
    if any(x in n for x in ("queria ","quero ","preciso ","me lembra","me ajuda","pode ")):return "request"
    if any(x in n for x in ("acho que","talvez","tava pensando","to pensando")):return "reflection"
    return "comment"
