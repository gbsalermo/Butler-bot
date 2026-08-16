import re
import unicodedata

from core_actions import add_grocery_items
from telegram_api import send_message

GROCERY_KB=[["➕ Adicionar item","📋 Ver itens faltando"],["🏠 Menu principal"]]

def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower()); value="".join(ch for ch in value if not unicodedata.combining(ch)); value=re.sub(r"[^a-z0-9, ]+"," ",value); return re.sub(r"\s+"," ",value).strip()
def _kb(rows):return {"keyboard":rows,"resize_keyboard":True}
def _row(row,key,default=None):
    if row is None:return default
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default
async def _rows(stmt):
    result=await stmt.all(); data=getattr(result,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []
async def _uid(db,chat_id):
    row=await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first(); return int(_row(row,"id")) if row else None
def _split_items(raw):
    raw=re.sub(r"^(?:o|a|os|as)\s+","",raw.strip()); return [x.strip() for x in re.split(r",|\s+e\s+",raw) if x.strip()]
async def _mark_bought(db,uid,requested_items):
    missing=await _rows(db.prepare("SELECT id,name FROM grocery_items WHERE user_id=? AND missing=1 ORDER BY name").bind(uid)); bought=[]; not_found=[]; used_ids=set()
    for requested in requested_items:
        target=_norm(requested); candidates=[]
        for row in missing:
            rid=int(_row(row,"id"))
            if rid in used_ids:continue
            name=_norm(_row(row,"name") or "")
            if target==name:candidates=[row]; break
            if target and name and (target in name or name in target):candidates.append(row)
        if len(candidates)==1:
            row=candidates[0]; rid=int(_row(row,"id")); await db.prepare("UPDATE grocery_items SET missing=0,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?").bind(rid,uid).run(); used_ids.add(rid); bought.append(_row(row,"name"))
        else:not_found.append(requested)
    return bought,not_found

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip(); n=_norm(text)
    if not n:return False
    uid=await _uid(db,int(chat_id))
    if not uid:return False

    # Relato de compra concluída é uma ação explícita sobre itens já existentes.
    bought_match=re.match(r"^(?:ja\s+)?(?:comprei|compramos|peguei|pegamos|trouxe|trouxemos)\s+(?:o|a|os|as\s+)?(.+)$",n)
    if bought_match:
        requested=_split_items(bought_match.group(1))
        if not requested:return False
        bought,not_found=await _mark_bought(db,uid,requested)
        if bought and not not_found:msg="✅ Tirei da lista: "+", ".join(bought)+". Logística doméstica funcionando, evento raro mas documentado."
        elif bought:msg="✅ Tirei da lista: "+", ".join(bought)+".\n\n🤨 Não achei com segurança: "+", ".join(not_found)+"."
        else:msg="🤨 Entendi a compra, mas não achei esses itens como faltantes. Não vou apagar no chute."
        await send_message(token,int(chat_id),msg,reply_markup=_kb(GROCERY_KB)); return True

    # Escrita direta só com comando explícito. Problemas como "acabou café" seguem
    # para suggestion_engine e pedem confirmação.
    m=re.match(r"^(?:comprar|compra|compre|bota na lista|coloca na lista|adiciona na lista)\s+(?:o|a|os|as\s+)?(.+)$",n)
    if not m:
        m=re.match(r"^(?:bota|coloca|adiciona)\s+(?:o|a|os|as\s+)?(.+?)\s+na lista$",n)
    if not m:return False
    items=_split_items(m.group(1))
    if not items:return False
    saved=await add_grocery_items(db,uid,items)
    if not saved:return False
    msg=(f"🛒 Anotado: {saved[0]}. Entrou na lista." if len(saved)==1 else "🛒 Anotado: "+", ".join(saved)+". Entraram na lista.")
    await send_message(token,int(chat_id),msg,reply_markup=_kb(GROCERY_KB)); return True
