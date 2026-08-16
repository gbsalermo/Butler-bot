import json
import random
import re
import unicodedata

import companion_nlu_v2 as v2
from core_actions import add_grocery_items, create_routine
from nlu import parse_time
from telegram_api import send_message
from knowledge.cooking import RECIPES
from knowledge.pop_culture import ENTRIES as POP_ENTRIES
from knowledge.philosophy import ENTRIES as PHILOSOPHY_ENTRIES
from knowledge.games import GAME_GUIDES, GAMES
from knowledge.books import BOOKS, AUTHOR_ALIASES

YES={"sim","pode","pode sim","faz","faz isso","bora","manda","manda ver","fechado","confirma"}
NO={"nao","não","deixa","cancela","melhor nao","melhor não"}
STOP={"quero","queria","uma","umas","um","uns","pra","para","por","com","sem","me","da","de","do","da","que","algo","alguma","algum","coisa","tipo","jogo","jogos","filme","filmes","serie","series","receita","receitas","livro","livros","ler","leitura","pc","computador","butler","indica","indique","recomenda","recomende","sugere","sugira"}


def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    value=re.sub(r"[^a-z0-9 ]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()


def _terms(text): return {x for x in _norm(text).split() if len(x)>=3 and x not in STOP}

def _row(row,key,default=None):
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default

async def _save_event(db,uid,event_type,payload): await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,?,?)").bind(uid,event_type,json.dumps(payload,ensure_ascii=False)).run()
async def _last_event(db,uid,event_type,hours=4):
    row=await db.prepare(f"SELECT id,detail FROM natural_events WHERE user_id=? AND event_type=? AND created_at>=datetime('now','-{int(hours)} hours') ORDER BY id DESC LIMIT 1").bind(uid,event_type).first()
    if not row:return None
    try:data=json.loads(_row(row,"detail") or "{}")
    except Exception:return None
    return int(_row(row,"id")),data
async def _set_pending(db,uid,action): await _save_event(db,uid,"library_pending",{"status":"pending","action":action})
async def _pending(db,uid):
    found=await _last_event(db,uid,"library_pending",3)
    if not found:return None
    event_id,data=found
    return (event_id,data) if data.get("status")=="pending" else None
async def _close_pending(db,event_id,data,status):
    data["status"]=status
    await db.prepare("UPDATE natural_events SET detail=? WHERE id=?").bind(json.dumps(data,ensure_ascii=False),event_id).run()

async def _execute(db,uid,action):
    kind=action.get("type"); payload=action.get("payload") or {}
    if kind=="grocery_add":
        items=await add_grocery_items(db,uid,payload.get("items") or [])
        if not items:return False,"Não achei item válido pra salvar."
        return True,"Coloquei na lista: "+", ".join(items)+"."
    if kind=="routine_create":
        name=str(payload.get("name") or "").strip()[:100]; tm=payload.get("time_hhmm")
        ok,status=await create_routine(db,uid,name,tm,payload.get("weekdays") or "todos os dias",payload.get("category") or "Lazer")
        if not ok:return False,"Não consegui validar a rotina: "+status+"."
        if status=="já existia":return True,f"A rotina `{name}` já existe; não dupliquei."
        return True,f"Rotina criada: {name}"+(f" às {tm}" if tm else "")+"."
    return False,"Essa ação não faz parte da biblioteca."

async def _handle_confirmation(db,token,chat_id,uid,text):
    pending=await _pending(db,uid)
    if not pending:return False
    n=_norm(text)
    if n not in YES and n not in NO:return False
    event_id,data=pending
    if n in NO:
        await _close_pending(db,event_id,data,"cancelled"); await send_message(token,chat_id,"Fechado. Não salvei nada. A biblioteca só sugeriu; quem manda ainda é você."); return True
    ok,msg=await _execute(db,uid,data.get("action") or {})
    await _close_pending(db,event_id,data,"executed" if ok else "rejected"); await send_message(token,chat_id,("Pronto. " if ok else "Não apliquei. ")+msg); return True


def _find_recipe(n):
    candidates=[]
    for key,data in RECIPES.items():
        for alias in data.get("aliases",[]):
            a=_norm(alias)
            if a and a in n:candidates.append((len(a),key,data))
    return max(candidates,default=(0,None,None),key=lambda x:x[0])[1:]

def _recipe_rank(n):
    wanted=_terms(n); ranked=[]
    for key,data in RECIPES.items():
        hay=" ".join([key]+data.get("aliases",[])+data.get("tags",[])+data.get("pantry_keys",[])); overlap=len(wanted & _terms(hay)); bonus=sum(2 for item in data.get("pantry_keys",[]) if _norm(item) in n); score=overlap+bonus
        if score>0:ranked.append((score,key,data))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True); return ranked[:4]
def _format_recipe(title,data):
    ing="\n".join("• "+x for x in data["ingredients"]); steps="\n".join(f"{i+1}. {x}" for i,x in enumerate(data["steps"])); return f"🍳 {title.title()} — {data['servings']}\n\nIngredientes\n{ing}\n\nPreparo\n{steps}\n\n💡 {data['tips']}"

def _find_pop(n):
    best=None
    for title,data in POP_ENTRIES.items():
        for alias in [title]+data.get("aliases",[]):
            a=_norm(alias)
            if a and a in n and (best is None or len(a)>best[0]):best=(len(a),title,data,a)
    return best[1:] if best else (None,None,None)
def _pop_rank(n,kind=None):
    wanted=_terms(n); ranked=[]
    for title,data in POP_ENTRIES.items():
        if kind and data.get("kind") not in kind:continue
        hay=" ".join([title]+data.get("aliases",[])+data.get("genres",[])+data.get("moods",[])); score=len(wanted & _terms(hay))
        if "curta" in n or "curto" in n:
            if data.get("episodes") and data.get("episodes")<=30:score+=3
            if data.get("kind")=="movie":score+=2
        if "comedia" in n and "comedia" in [_norm(x) for x in data.get("genres",[])]:score+=2
        if score>0:ranked.append((score,title,data))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True); return ranked[:5]
def _game_rank(n):
    wanted=_terms(n); ranked=[]
    for title,data in GAMES.items():
        hay=" ".join([title,data.get("weight","")]+data.get("platforms",[])+data.get("genres",[])+data.get("modes",[])+data.get("tags",[])); score=len(wanted & _terms(hay))
        if any(x in n for x in ("leve","fraco","pc fraco","notebook fraco")) and data.get("weight") in ("leve","leve-medio"):score+=3
        if any(x in n for x in ("com amigos","coop","cooperativo","multiplayer")) and any(x in data.get("modes",[]) for x in ("coop","multiplayer")):score+=3
        if "pc" in n and "pc" in data.get("platforms",[]):score+=1
        if score>0:ranked.append((score,title,data))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True); return ranked[:5]
def _find_philosophy(n):
    best=None
    for title,data in PHILOSOPHY_ENTRIES.items():
        for alias in data.get("aliases",[]):
            a=_norm(alias)
            if a and a in n and (best is None or len(a)>best[0]):best=(len(a),title,data)
    return best[1:] if best else (None,None)

def _find_book(n):
    best=None
    for title,data in BOOKS.items():
        aliases=[title,data.get("author","")]
        for alias in aliases:
            a=_norm(alias)
            if a and a in n and (best is None or len(a)>best[0]):best=(len(a),title,data)
    return best[1:] if best else (None,None)

def _book_rank(n):
    wanted=_terms(n); ranked=[]
    author_titles=set()
    for alias,titles in AUTHOR_ALIASES.items():
        if _norm(alias) in n:author_titles.update(titles)
    for title,data in BOOKS.items():
        hay=" ".join([title,data.get("author",""),data.get("country",""),data.get("kind","")]+data.get("tags",[])); score=len(wanted & _terms(hay))
        if title in author_titles:score+=5
        if any(x in n for x in ("brasileiro","brasileira","brasil")) and "literatura brasileira" in data.get("tags",[]):score+=3
        if "classico" in n and "classico" in data.get("tags",[]):score+=2
        if any(x in n for x in ("curto","curta","rapido","rápido")) and "curto" in data.get("tags",[]):score+=3
        if "filosofia" in n and (data.get("kind")=="filosofia" or "filosofia" in data.get("tags",[])):score+=3
        if any(x in n for x in ("bukowski","on the road","beat","estrada","contracultura","cru")) and any(x in data.get("tags",[]) for x in ("bukowski","bukowski-like","beat","estrada","contracultura","cru","dirty realism")):score+=3
        if score>0:ranked.append((score,title,data))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True); return ranked[:5]
def _format_book(title,data): return f"📚 {title.title()} — {data['author']}\n\n{data['summary']}"
def _is_info_question(n):
    starts=("quem ","quem foi ","quem era ","o que ","oq ","qual a desse ","qual e a desse ","me fala ","fala sobre ","me explica ","me fale ")
    return any(x in n for x in starts) or "era quem" in n or "e quem mesmo" in n

async def _handle_recipe_followup(db,token,chat_id,uid,text,n):
    ctx=await _last_event(db,uid,"library_context",4)
    if not ctx or ctx[1].get("domain")!="recipe":return False
    data=ctx[1]
    if not any(x in n for x in ("nao tenho","não tenho","to sem","tô sem","falta","acabou")):return False
    pantry=data.get("pantry_keys") or []; missing=[item for item in pantry if _norm(item) in n]
    if not missing:
        m=re.search(r"(?:nao tenho|não tenho|to sem|tô sem|falta|acabou)\s+(?:o|a|os|as)?\s*(.+)$",text,flags=re.I)
        if m:
            raw=m.group(1).strip(" .,!?"); missing=[raw] if raw and len(raw)<=80 else []
    if not missing: await send_message(token,chat_id,"Qual ingrediente está faltando? Se estiver na receita eu consigo jogar direto na lista depois."); return True
    await _set_pending(db,uid,{"type":"grocery_add","payload":{"items":missing}}); await send_message(token,chat_id,f"Tá faltando {', '.join(missing)}. Quer que eu coloque isso na lista de itens faltando? Manda `pode` ou `deixa`."); return True

async def _handle_series_followup(db,token,chat_id,uid,text,n):
    ctx=await _last_event(db,uid,"library_context",4)
    if not ctx or ctx[1].get("domain")!="series":return False
    data=ctx[1]; title=data.get("title")
    if not title:return False
    if any(x in n for x in ("quero assistir ela toda","quero ver ela toda","quero assistir tudo","quero ver tudo","vou assistir toda","vou ver toda","quero maratonar")):
        tm=parse_time(text)
        if tm: await _set_pending(db,uid,{"type":"routine_create","payload":{"name":f"Assistir {title}","category":"Lazer","weekdays":"todos os dias","time_hhmm":tm}}); await send_message(token,chat_id,f"Dá pra transformar isso numa rotina diária às {tm}: `Assistir {title}`. Confirmo? `pode` ou `deixa`.")
        else: await _save_event(db,uid,"library_setup",{"kind":"series_watch_time","title":title}); await send_message(token,chat_id,f"Rapaz, {data.get('episodes','um bocado de')} episódios é compromisso sério. Posso criar uma rotina diária pra assistir {title}. Que horas costuma ser bom pra você?")
        return True
    setup=await _last_event(db,uid,"library_setup",2)
    if setup and setup[1].get("kind")=="series_watch_time":
        tm=parse_time(text)
        if tm:
            stitle=setup[1].get("title") or title; await _set_pending(db,uid,{"type":"routine_create","payload":{"name":f"Assistir {stitle}","category":"Lazer","weekdays":"todos os dias","time_hhmm":tm}}); await send_message(token,chat_id,f"Então fica diariamente às {tm}: `Assistir {stitle}`. Confirmo? `pode` ou `deixa`."); return True
    return False

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    if await _handle_confirmation(db,token,int(chat_id),uid,text):return True
    n=_norm(text)
    if await _handle_recipe_followup(db,token,int(chat_id),uid,text,n):return True
    if await _handle_series_followup(db,token,int(chat_id),uid,text,n):return True

    recipe_name,recipe=_find_recipe(n)
    if recipe and any(x in n for x in ("receita","como fazer","como faz","quero fazer","me ensina")):
        await _save_event(db,uid,"library_context",{"domain":"recipe","title":recipe_name,"pantry_keys":recipe.get("pantry_keys",[])}); await send_message(token,int(chat_id),_format_recipe(recipe_name,recipe)); return True
    if any(x in n for x in ("o que faco","o que faço","o que da pra fazer","o que dá pra fazer","ideia de receita","receita com","tenho ")):
        ranked=_recipe_rank(n)
        if ranked: await send_message(token,int(chat_id),"🍳 Com isso eu tenho algumas rotas:\n"+"\n".join(f"• {x[1].title()}" for x in ranked[:4])+"\n\nSe escolher uma, eu puxo a receita completa."); return True

    if any(x in n for x in ("time pokemon","time de pokemon","time aleatorio","time aleatório","monta um time")) and any(x in n for x in ("fire red","firered","pokemon")):
        guide=GAME_GUIDES["pokemon firered"]; team=random.sample(guide["team_pool"],6); await _save_event(db,uid,"library_context",{"domain":"game","title":"Pokémon FireRed","team":team}); await send_message(token,int(chat_id),"🎮 Time aleatório pra FireRed:\n"+"\n".join(f"• {p}" for p in team)+"\n\nSe esse RH de Kanto der ruim, eu sorteio outro."); return True
    if any(x in n for x in ("me indica um jogo","me indica jogo","recomenda um jogo","recomenda jogo","jogo pra pc","jogo para pc","quero um jogo","algum jogo")):
        ranked=_game_rank(n) or [(1,k,v) for k,v in random.sample(list(GAMES.items()),min(5,len(GAMES)))]; await send_message(token,int(chat_id),"🎮 Eu iria por aqui:\n\n"+"\n".join(f"• {title.title()} — {data['summary']}" for _,title,data in ranked[:5])); return True

    book_title,book=_find_book(n)
    if book and (_is_info_question(n) or any(x in n for x in ("livro","vale a pena","sobre o que","do que fala"))):
        await _save_event(db,uid,"library_context",{"domain":"book","title":book_title.title(),"author":book.get("author")}); await send_message(token,int(chat_id),_format_book(book_title,book)); return True
    if any(x in n for x in ("me indica um livro","me indica livro","recomenda um livro","recomenda livro","quero um livro","o que eu leio","o que ler","algo pra ler","algo para ler")):
        ranked=_book_rank(n)
        if not ranked: ranked=random.sample([(1,k,v) for k,v in BOOKS.items()],min(5,len(BOOKS)))
        lines=[f"• {title.title()} — {data['author']} — {data['summary']}" for _,title,data in ranked[:5]]
        await send_message(token,int(chat_id),"📚 Pra essa vibe, eu olharia estes:\n\n"+"\n".join(lines)); return True

    pop_title,pop,matched=_find_pop(n)
    if pop and (_is_info_question(n) or matched==_norm(text)):
        answer=(pop.get("details") or {}).get(matched) or pop.get("summary"); payload={"domain":"series" if pop.get("kind")=="series" else "culture","title":pop_title.title()}
        if pop.get("episodes"):payload["episodes"]=pop["episodes"]
        if pop.get("seasons"):payload["seasons"]=pop["seasons"]
        await _save_event(db,uid,"library_context",payload); suffix=f"\n\n📺 {pop.get('seasons')} temporada(s), {pop.get('episodes')} episódios no total." if pop.get("kind")=="series" and pop.get("episodes") else ""; await send_message(token,int(chat_id),answer+suffix); return True
    if any(x in n for x in ("me indica um filme","me indica filme","recomenda filme","quero um filme","me indica uma serie","me indica série","recomenda serie","recomenda série","quero uma serie","quero uma série")):
        want_series="serie" in n or "série" in text.lower(); kinds=("series",) if want_series else ("movie","film_series","franchise"); ranked=_pop_rank(n,kinds)
        if not ranked:
            pool=[(1,k,v) for k,v in POP_ENTRIES.items() if v.get("kind") in kinds]; ranked=random.sample(pool,min(5,len(pool))) if pool else []
        lines=[f"• {title.title()} — {data['summary']}" for _,title,data in ranked[:5]]
        if lines: await send_message(token,int(chat_id),("📺 " if want_series else "🎬 ")+"Eu começaria por:\n\n"+"\n".join(lines)); return True

    phil_title,phil=_find_philosophy(n)
    if phil and _is_info_question(n): await _save_event(db,uid,"library_context",{"domain":"philosophy","title":phil_title}); await send_message(token,int(chat_id),phil["summary"]); return True
    return False
