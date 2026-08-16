import json
import re
import unicodedata

import companion_nlu_v2 as v2
from telegram_api import send_message
from knowledge.cooking import RECIPES as BASE_RECIPES
from knowledge.cooking_pasta import PASTA_RECIPES

RECIPES = {**BASE_RECIPES, **PASTA_RECIPES}
STOP = {"receita","receitas","me","indica","indique","recomenda","recomende","quero","uma","umas","de","do","da","com","para","pra","algo","ideia","ideias","butler"}


def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    value=re.sub(r"[^a-z0-9 ]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()


def _terms(text):
    return {x for x in _norm(text).split() if len(x)>=3 and x not in STOP}


def _find_exact(n):
    best=None
    for title,data in RECIPES.items():
        for alias in [title]+data.get("aliases",[]):
            a=_norm(alias)
            if a and a in n and (best is None or len(a)>best[0]):
                best=(len(a),title,data)
    return best[1:] if best else (None,None)


def _rank(n):
    wanted=_terms(n); ranked=[]
    for title,data in RECIPES.items():
        hay=" ".join([title]+data.get("aliases",[])+data.get("tags",[])+data.get("pantry_keys",[]))
        score=len(wanted & _terms(hay))
        for token in wanted:
            if token in _norm(hay):score+=1
        if score>0:ranked.append((score,title,data))
    ranked.sort(key=lambda x:(x[0],x[1]),reverse=True)
    return ranked[:6]


def _format_recipe(title,data):
    ingredients="\n".join("• "+x for x in data.get("ingredients",[]))
    steps="\n".join(f"{i+1}. {x}" for i,x in enumerate(data.get("steps",[])))
    return f"🍳 {title.title()} — {data.get('servings','')}\n\nIngredientes\n{ingredients}\n\nPreparo\n{steps}\n\n💡 {data.get('tips','')}"


async def _remember_context(db,uid,title,data):
    payload=json.dumps({"domain":"recipe","title":title,"pantry_keys":data.get("pantry_keys",[])},ensure_ascii=False)
    await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'library_context',?)").bind(uid,payload).run()


async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    n=_norm(text)
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False

    # Receita específica, inclusive das extensões do catálogo.
    title,data=_find_exact(n)
    if data and any(x in n for x in ("receita","como fazer","como faz","me ensina","quero fazer")):
        await _remember_context(db,uid,title,data)
        await send_message(token,int(chat_id),_format_recipe(title,data))
        return True

    # Consulta de categoria: "receitas de macarrão", "me indica receitas de frango", "ideias de sobremesa".
    category_request = (
        re.search(r"\breceitas?\s+(?:de|com)\s+",n)
        or re.search(r"\b(?:indica|indique|recomenda|recomende)\s+(?:umas?\s+)?receitas?\b",n)
        or re.search(r"\bideias?\s+(?:de|com|para)\b",n)
    )
    if category_request:
        ranked=_rank(n)
        if ranked:
            lines=[]
            for _,rtitle,rdata in ranked[:5]:
                tags=rdata.get("tags",[])
                hint=(" — "+", ".join(tags[:2])) if tags else ""
                lines.append(f"• {rtitle.title()}{hint}")
            await send_message(token,int(chat_id),"🍝 Tenho algumas boas rotas:\n"+"\n".join(lines)+"\n\nManda o nome de uma delas com `receita de ...` que eu passo completa.")
            return True
        await send_message(token,int(chat_id),"Não achei uma receita boa dessa categoria no meu acervo ainda. Melhor admitir do que inventar jantar.")
        return True
    return False
