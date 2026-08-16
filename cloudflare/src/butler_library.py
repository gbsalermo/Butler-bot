import json
import random
import re
import unicodedata

import companion_nlu_v2 as v2
from nlu import parse_time
from telegram_api import send_message
from knowledge.cooking import RECIPES
from knowledge.pop_culture import ENTRIES as POP_ENTRIES
from knowledge.philosophy import ENTRIES as PHILOSOPHY_ENTRIES
from knowledge.games import GAME_GUIDES

YES={"sim","pode","pode sim","faz","faz isso","bora","manda","manda ver","fechado","confirma"}
NO={"nao","não","deixa","cancela","melhor nao","melhor não"}


def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    value=re.sub(r"[^a-z0-9 ]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()


def _row(row,key,default=None):
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default


async def _save_event(db,uid,event_type,payload):
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,?,?)").bind(uid,event_type,json.dumps(payload,ensure_ascii=False)).run()


async def _last_event(db,uid,event_type,hours=4):
    row=await db.prepare(f"SELECT id,detail FROM natural_events WHERE user_id=? AND event_type=? AND created_at>=datetime('now','-{int(hours)} hours') ORDER BY id DESC LIMIT 1").bind(uid,event_type).first()
    if not row:return None
    try:data=json.loads(_row(row,"detail") or "{}")
    except Exception:return None
    return int(_row(row,"id")),data


async def _set_pending(db,uid,action):
    await _save_event(db,uid,"library_pending",{"status":"pending","action":action})


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
        items=[str(x).strip()[:80] for x in (payload.get("items") or []) if str(x).strip()][:10]
        if not items:return False,"Não achei item válido pra salvar."
        for item in items:
            await db.prepare("INSERT INTO grocery_items(user_id,name,missing) VALUES(?,?,1) ON CONFLICT(user_id,name) DO UPDATE SET missing=1,updated_at=CURRENT_TIMESTAMP").bind(uid,item).run()
        return True,"Coloquei na lista: "+", ".join(items)+"."
    if kind=="routine_create":
        name=str(payload.get("name") or "").strip()[:100]
        tm=payload.get("time_hhmm")
        weekdays=str(payload.get("weekdays") or "todos os dias")[:120]
        category=str(payload.get("category") or "Lazer")[:60]
        if not name:return False,"A rotina veio sem nome."
        if tm and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",str(tm)):return False,"Esse horário veio estranho."
        exists=await db.prepare("SELECT id FROM routines WHERE user_id=? AND lower(name)=lower(?) AND active=1 LIMIT 1").bind(uid,name).first()
        if exists:return True,f"A rotina `{name}` já existe; não dupliquei."
        await db.prepare("INSERT INTO routines(user_id,name,category,time_hhmm,weekdays,active) VALUES(?,?,?,?,?,1)").bind(uid,name,category,tm,weekdays).run()
        return True,f"Rotina criada: {name}"+(f" às {tm}" if tm else "")+"."
    return False,"Essa ação não faz parte da biblioteca."


async def _handle_confirmation(db,token,chat_id,uid,text):
    pending=await _pending(db,uid)
    if not pending:return False
    n=_norm(text)
    if n not in YES and n not in NO:return False
    event_id,data=pending
    if n in NO:
        await _close_pending(db,event_id,data,"cancelled")
        await send_message(token,chat_id,"Fechado. Não salvei nada. A biblioteca só sugeriu; quem manda ainda é você.")
        return True
    ok,msg=await _execute(db,uid,data.get("action") or {})
    await _close_pending(db,event_id,data,"executed" if ok else "rejected")
    await send_message(token,chat_id,("Pronto. " if ok else "Não apliquei. ")+msg)
    return True


def _find_recipe(n):
    candidates=[]
    for key,data in RECIPES.items():
        for alias in data.get("aliases",[]):
            a=_norm(alias)
            if a and a in n:candidates.append((len(a),key,data))
    return max(candidates,default=(0,None,None),key=lambda x:x[0])[1:]


def _format_recipe(title,data):
    ing="\n".join("• "+x for x in data["ingredients"])
    steps="\n".join(f"{i+1}. {x}" for i,x in enumerate(data["steps"]))
    return f"🍳 {title.title()} — {data['servings']}\n\nIngredientes\n{ing}\n\nPreparo\n{steps}\n\n💡 {data['tips']}"


def _find_pop(n):
    best=None
    for title,data in POP_ENTRIES.items():
        for alias in [title]+data.get("aliases",[]):
            a=_norm(alias)
            if a and a in n and (best is None or len(a)>best[0]):best=(len(a),title,data,a)
    return best[1:] if best else (None,None,None)


def _find_philosophy(n):
    best=None
    for title,data in PHILOSOPHY_ENTRIES.items():
        for alias in data.get("aliases",[]):
            a=_norm(alias)
            if a and a in n and (best is None or len(a)>best[0]):best=(len(a),title,data)
    return best[1:] if best else (None,None)


def _is_info_question(n):
    starts=("quem ","quem foi ","quem era ","o que ","oq ","qual a desse ","qual e a desse ","me fala ","fala sobre ","me explica ","me fale ")
    return any(x in n for x in starts) or "era quem" in n or "e quem mesmo" in n


async def _handle_recipe_followup(db,token,chat_id,uid,text,n):
    ctx=await _last_event(db,uid,"library_context",4)
    if not ctx:return False
    _,data=ctx
    if data.get("domain")!="recipe":return False
    if not any(x in n for x in ("nao tenho","não tenho","to sem","tô sem","falta","acabou")):return False
    pantry=data.get("pantry_keys") or []
    missing=[]
    for item in pantry:
        if _norm(item) in n:missing.append(item)
    if not missing:
        # Tenta capturar o trecho depois de 'não tenho/to sem/falta'.
        m=re.search(r"(?:nao tenho|não tenho|to sem|tô sem|falta|acabou)\s+(?:o|a|os|as)?\s*(.+)$",text,flags=re.I)
        if m:
            raw=m.group(1).strip(" .,!?")
            if raw and len(raw)<=80:missing=[raw]
    if not missing:
        await send_message(token,chat_id,"Qual ingrediente está faltando? Se estiver na receita eu consigo jogar direto na lista depois.")
        return True
    await _set_pending(db,uid,{"type":"grocery_add","payload":{"items":missing}})
    await send_message(token,chat_id,f"Tá faltando {', '.join(missing)}. Quer que eu coloque isso na lista de itens faltando? Manda `pode` ou `deixa`.")
    return True


async def _handle_series_followup(db,token,chat_id,uid,text,n):
    ctx=await _last_event(db,uid,"library_context",4)
    if not ctx:return False
    _,data=ctx
    if data.get("domain")!="series":return False
    title=data.get("title")
    if not title:return False
    if any(x in n for x in ("quero assistir ela toda","quero ver ela toda","quero assistir tudo","quero ver tudo","vou assistir toda","vou ver toda","quero maratonar")):
        tm=parse_time(text)
        if tm:
            await _set_pending(db,uid,{"type":"routine_create","payload":{"name":f"Assistir {title}","category":"Lazer","weekdays":"todos os dias","time_hhmm":tm}})
            await send_message(token,chat_id,f"Dá pra transformar isso numa rotina diária às {tm}: `Assistir {title}`. Confirmo? `pode` ou `deixa`.")
        else:
            await _save_event(db,uid,"library_setup",{"kind":"series_watch_time","title":title})
            await send_message(token,chat_id,f"Rapaz, {data.get('episodes','um bocado de')} episódios é compromisso sério. Posso criar uma rotina diária pra assistir {title}. Que horas costuma ser bom pra você?")
        return True
    setup=await _last_event(db,uid,"library_setup",2)
    if setup and setup[1].get("kind")=="series_watch_time":
        tm=parse_time(text)
        if tm:
            stitle=setup[1].get("title") or title
            await _set_pending(db,uid,{"type":"routine_create","payload":{"name":f"Assistir {stitle}","category":"Lazer","weekdays":"todos os dias","time_hhmm":tm}})
            await send_message(token,chat_id,f"Então fica diariamente às {tm}: `Assistir {stitle}`. Confirmo? `pode` ou `deixa`.")
            return True
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
        await _save_event(db,uid,"library_context",{"domain":"recipe","title":recipe_name,"pantry_keys":recipe.get("pantry_keys",[])})
        await send_message(token,int(chat_id),_format_recipe(recipe_name,recipe)); return True

    if any(x in n for x in ("time pokemon","time de pokemon","time aleatorio","time aleatório","monta um time")) and any(x in n for x in ("fire red","firered","pokemon")):
        guide=GAME_GUIDES["pokemon firered"]
        team=random.sample(guide["team_pool"],6)
        await _save_event(db,uid,"library_context",{"domain":"game","title":"Pokémon FireRed","team":team})
        await send_message(token,int(chat_id),"🎮 Time aleatório pra FireRed:\n"+"\n".join(f"• {p}" for p in team)+"\n\nSe esse RH de Kanto der ruim, eu sorteio outro."); return True

    pop_title,pop,matched=_find_pop(n)
    if pop and (_is_info_question(n) or matched==_norm(text)):
        answer=(pop.get("details") or {}).get(matched) or pop.get("summary")
        payload={"domain":"series" if pop.get("kind")=="series" else "culture","title":pop_title.title()}
        if pop.get("episodes"):payload["episodes"]=pop["episodes"]
        if pop.get("seasons"):payload["seasons"]=pop["seasons"]
        await _save_event(db,uid,"library_context",payload)
        suffix=""
        if pop.get("kind")=="series" and pop.get("episodes"):
            suffix=f"\n\n📺 {pop.get('seasons')} temporada(s), {pop.get('episodes')} episódios no total."
        await send_message(token,int(chat_id),answer+suffix); return True

    phil_title,phil=_find_philosophy(n)
    if phil and _is_info_question(n):
        await _save_event(db,uid,"library_context",{"domain":"philosophy","title":phil_title})
        await send_message(token,int(chat_id),phil["summary"]); return True

    return False
