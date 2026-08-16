import re
import unicodedata

import companion_nlu_v2 as v2
import butler_library as library
from knowledge.cooking_books import COOKING_BOOKS
from knowledge.meat_cuts import MEAT_CUTS, MEAT_RECIPES
from telegram_api import send_message

STOP={"o","a","os","as","um","uma","uns","umas","de","da","do","das","dos","com","pra","para","por","que","eu","me","meu","minha","queria","quero","fazer","faco","faço","algo","alguma","coisa","receita","receitas","ideia","ideias","butler","pode","posso","resto","sobra"}

def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower()); value="".join(ch for ch in value if not unicodedata.combining(ch)); value=re.sub(r"[^a-z0-9 ]+"," ",value); return re.sub(r"\s+"," ",value).strip()
def _terms(text): return {x for x in _norm(text).split() if len(x)>=3 and x not in STOP}
def _all_recipes():
    for book,meta in COOKING_BOOKS.items():
        for title,data in meta.get("recipes",{}).items(): yield book,title,data
    for title,data in MEAT_RECIPES.items(): yield "carnes",title,data
def _find_exact(n):
    best=None
    for book,title,data in _all_recipes():
        for alias in [title]+data.get("aliases",[]):
            a=_norm(alias)
            if a and (n==a or a in n):
                score=len(a)+(8 if n==a else 0)
                if best is None or score>best[0]:best=(score,book,title,data)
    return best[1:] if best else (None,None,None)
def _find_cut(n):
    best=None
    for name,data in MEAT_CUTS.items():
        for alias in [name]+data.get("aliases",[]):
            a=_norm(alias)
            if a and (n==a or a in n):
                score=len(a)+(10 if n==a else 0)
                if best is None or score>best[0]:best=(score,name,data)
    return best[1:] if best else (None,None)
def _book_for_query(n):
    best=None
    for book,meta in COOKING_BOOKS.items():
        for alias in [book]+meta.get("aliases",[]):
            a=_norm(alias)
            if a and a in n and (best is None or len(a)>best[0]):best=(len(a),book,meta)
    if any(_norm(a) in n for d in MEAT_CUTS.values() for a in d.get("aliases",[])): return "carnes",COOKING_BOOKS.get("carnes",{})
    return best[1:] if best else (None,None)
def _rank(n,book_filter=None):
    wanted=_terms(n); ranked=[]; leftovers=any(x in n for x in ("resto","sobra","sobrou","de ontem","ontem")); quick=any(x in n for x in ("rapido","facil","simples")); light=any(x in n for x in ("leve","saudavel"))
    cut_name,cut=_find_cut(n); preferred=set(cut.get("best_for",[])) if cut else set()
    for book,title,data in _all_recipes():
        if book_filter and book!=book_filter:continue
        hay=" ".join([book,title]+data.get("aliases",[])+data.get("tags",[])+data.get("ingredients",[])); score=len(wanted&_terms(hay))*2; nhay=_norm(hay)
        for term in wanted:
            if term in nhay:score+=1
        tags={_norm(x) for x in data.get("tags",[])}
        if leftovers and "aproveitamento" in tags:score+=5
        if quick and ("rapido" in tags or "simples" in tags):score+=3
        if light and "leve" in tags:score+=3
        if preferred and any(_norm(use) in nhay or _norm(use)==_norm(title) for use in preferred):score+=5
        if cut_name and _norm(cut_name) in nhay:score+=7
        if score>0:ranked.append((score,book,title,data))
    ranked.sort(key=lambda x:(x[0],x[2]),reverse=True); return ranked[:6]
def _format(title,data):
    ingredients="\n".join("• "+x for x in data.get("ingredients",[])); steps="\n".join(f"{i+1}. {x}" for i,x in enumerate(data.get("steps",[]))); return f"🍳 {title.title()}\n\nIngredientes\n{ingredients}\n\nPreparo\n{steps}\n\n💡 {data.get('tips','')}"
def _format_cut(name,data):
    uses=", ".join(x.replace("_"," ").title() for x in data.get("best_for",[])); return f"🥩 {name.title()} — {data.get('kind','carne')}\n\n{data.get('profile','')}\n\nVai bem para: {uses}.\nPreparo: {data.get('cooking','')}"
def _is_cooking_request(n):
    direct=("como fazer","como faz","como preparo","como preparar","receita de","receita do","receita da","receitas de","receitas com")
    informal=("queria fazer","quero fazer","oq posso fazer","o que posso fazer","o que da pra fazer","alguma ideia","me da uma ideia","tenho ","sobrou ","sobra de ","resto de ","da pra fazer com","o que faco com","oq faco com")
    return any(x in n for x in direct+informal)
async def _save_recipe_context(db,uid,book,title,data): await library._save_event(db,uid,"library_context",{"domain":"recipe","book":book,"title":title,"pantry_keys":data.get("ingredients",[])[:20]})
async def _followup_missing(db,token,chat_id,uid,text,n):
    ctx=await library._last_event(db,uid,"library_context",4)
    if not ctx or ctx[1].get("domain")!="recipe":return False
    if not any(x in n for x in ("nao tenho","to sem","estou sem","falta","acabou")):return False
    m=re.search(r"(?:nao tenho|não tenho|to sem|tô sem|estou sem|falta|acabou)\s+(?:o|a|os|as)?\s*(.+)$",text,flags=re.I)
    if not m:return False
    missing=m.group(1).strip(" .,!?")[:80]
    if not missing:return False
    await library._set_pending(db,uid,{"type":"grocery_add","payload":{"items":[missing]}}); await send_message(token,chat_id,f"Tá sem {missing}. Quer que eu jogue isso na lista de itens faltando? Manda `pode` ou `deixa`."); return True
async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=_norm(text)
    if await _followup_missing(db,token,int(chat_id),uid,text,n):return True
    book,title,data=_find_exact(n); explicit_recipe=any(x in n for x in ("como fazer","como faz","como preparo","como preparar","receita","me ensina")); recent=await library._last_event(db,uid,"cooking_search",2)
    if data and (explicit_recipe or n in {_norm(title)}|{_norm(x) for x in data.get("aliases",[])} or recent):
        await _save_recipe_context(db,uid,book,title,data); await send_message(token,int(chat_id),_format(title,data)); return True
    cut_name,cut=_find_cut(n)
    # Um corte/preparação sozinho é conhecimento válido: "filé mignon", "músculo", "carne do sol".
    if cut and (n in {_norm(cut_name)}|{_norm(x) for x in cut.get("aliases",[])} or any(x in n for x in ("o que e","oq e","como fazer","como preparo","o que faco","oq faco","receita","ideia","serve pra","bom pra"))):
        if any(x in n for x in ("como fazer","como preparo","o que faco","oq faco","receita","ideia","serve pra","bom pra")):
            ranked=_rank(n,"carnes")
            if ranked:
                await library._save_event(db,uid,"cooking_search",{"query":text,"book":"carnes","cut":cut_name,"results":[x[2] for x in ranked[:6]]}); lines="\n".join(f"• {x[2].title()}" for x in ranked[:6]); await send_message(token,int(chat_id),_format_cut(cut_name,cut)+"\n\n🍳 Algumas rotas:\n"+lines+"\n\nManda o nome de uma que eu abro a receita."); return True
        await send_message(token,int(chat_id),_format_cut(cut_name,cut)); return True
    book_name,book_meta=_book_for_query(n)
    if not _is_cooking_request(n) and not (book_name and any(x in n for x in ("receita","receitas","queria","quero"))):return False
    ranked=_rank(n,book_name)
    if not ranked and book_name:ranked=[(1,book_name,t,d) for t,d in list(book_meta.get("recipes",{}).items())[:6]]
    if not ranked:return False
    await library._save_event(db,uid,"cooking_search",{"query":text,"book":book_name,"results":[x[2] for x in ranked[:6]]}); lines=[]
    for _,book,title,data in ranked[:6]:
        tags=", ".join(data.get("tags",[])[:3]); lines.append(f"• {title.title()}"+(f" — {tags}" if tags else ""))
    intro=f"🍳 No livro de {book_name}, eu tenho essas boas rotas:" if book_name else "🍳 Dá pra trabalhar com isso. Eu iria por aqui:"
    await send_message(token,int(chat_id),intro+"\n"+"\n".join(lines)+"\n\nManda só o nome de uma delas que eu abro a receita completa."); return True
