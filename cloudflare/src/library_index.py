"""Índice comum da Butler Library.

Normaliza catálogos diferentes em records pesquisáveis. Novas entradas herdam busca
por nome, aliases, tags, gêneros, autor, resumo e metadados sem lógica específica.
"""
import re
import unicodedata

from knowledge.games import GAMES, GAME_GUIDES
from knowledge.pop_culture import ENTRIES as POP_ENTRIES
from knowledge.books import BOOKS
from knowledge.philosophy import ENTRIES as PHILOSOPHY_ENTRIES

STOP={"me","um","uma","de","do","da","para","pra","por","com","sem","que","quem","qual","quero","queria","indica","recomenda","sugere","fala","sobre","explica","livro","jogo","filme","serie","butler"}

def _norm(text):
    v=unicodedata.normalize("NFKD",(text or "").lower()); v="".join(c for c in v if not unicodedata.combining(c)); v=re.sub(r"[^a-z0-9 ]+"," ",v); return re.sub(r"\s+"," ",v).strip()
def _terms(text):return {x for x in _norm(text).split() if len(x)>=3 and x not in STOP}

def records():
    out=[]
    for name,data in GAMES.items():
        out.append({"domain":"games","name":name,"aliases":[name],"summary":data.get("summary",""),"tags":data.get("genres",[])+data.get("modes",[])+data.get("tags",[])+data.get("platforms",[])+[data.get("weight","")],"meta":data})
    for name,data in GAME_GUIDES.items():
        out.append({"domain":"games","name":name,"aliases":data.get("aliases",[name]),"summary":data.get("summary",""),"tags":data.get("tips",[]),"meta":data})
    for name,data in POP_ENTRIES.items():
        aliases=list(dict.fromkeys([name]+data.get("aliases",[])))
        out.append({"domain":"movies_series","name":name,"aliases":aliases,"summary":data.get("summary",""),"tags":data.get("genres",[])+data.get("moods",[])+[data.get("kind","")],"meta":data})
        for alias,detail in (data.get("details") or {}).items():
            out.append({"domain":"culture","name":alias,"aliases":[alias],"summary":detail,"tags":[name]+data.get("genres",[]),"meta":{"parent":name,"kind":"character"}})
    for name,data in BOOKS.items():
        out.append({"domain":"books","name":name,"aliases":[name,data.get("author","")],"summary":data.get("summary",""),"tags":data.get("tags",[])+[data.get("author",""),data.get("country",""),data.get("kind","")],"meta":data})
    for name,data in PHILOSOPHY_ENTRIES.items():
        out.append({"domain":"culture","name":name,"aliases":data.get("aliases",[name]),"summary":data.get("summary",""),"tags":data.get("topics",[])+data.get("tags",[]),"meta":data})
    return out

_RECORDS=None
def all_records():
    global _RECORDS
    if _RECORDS is None:_RECORDS=records()
    return _RECORDS

def search(text,domain=None,limit=5):
    n=_norm(text); wanted=_terms(text); ranked=[]
    domains=None
    if domain:
        domains={domain}
        if domain=="movies_series":domains.add("culture")
        if domain=="culture":domains|={"movies_series","books"}
    for rec in all_records():
        if domains and rec["domain"] not in domains:continue
        score=0; exact=False
        for alias in rec.get("aliases",[]):
            a=_norm(alias)
            if not a:continue
            if n==a:score+=20; exact=True
            elif re.search(r"\b"+re.escape(a)+r"\b",n):score+=12
        hay=" ".join([rec["name"],rec.get("summary","")]+[str(x) for x in rec.get("tags",[]) if x]); terms=_terms(hay)
        score+=len(wanted & terms)*2
        # Filtrar por domínio não é evidência semântica. O bônus só desempata
        # resultados que já casaram com alias, termo, tag, autor, gênero etc.
        if score<=0:continue
        if domain and rec["domain"]==domain:score+=2
        ranked.append((score,exact,rec))
    ranked.sort(key=lambda x:(x[0],x[1],x[2]["name"]),reverse=True)
    return [r for _,_,r in ranked[:limit]]
