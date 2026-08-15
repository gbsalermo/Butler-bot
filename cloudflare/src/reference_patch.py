import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from nlu import parse_date, parse_time
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ=timezone(timedelta(hours=UTC_OFFSET_HOURS))
MAIN_KB=[["🌙 Day-off"],["➕ Adicionar","🗓️ Hoje"],["🛒 Item faltando","📚 Matérias"],["🏠 Cotidiano","🏋️ Musculação"]]

def _norm(text):
    v=unicodedata.normalize("NFKD",(text or "").lower());v="".join(c for c in v if not unicodedata.combining(c));return re.sub(r"\s+"," ",v).strip()
def _row(row,key,default=None):
    if row is None:return default
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default
async def _rows(stmt):
    r=await stmt.all();d=getattr(r,"results",None)
    if d is None:return []
    try:return list(d)
    except Exception:return d.to_py() if hasattr(d,"to_py") else []
def _kb(rows):return {"keyboard":rows,"resize_keyboard":True}
def _now():return datetime.now(timezone.utc).astimezone(LOCAL_TZ)
async def _uid(db,chat):
    r=await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat).first();return int(_row(r,"id")) if r else None
async def _ctx(db,uid):
    r=await db.prepare("SELECT detail FROM natural_events WHERE user_id=? AND event_type='context' ORDER BY id DESC LIMIT 1").bind(uid).first()
    try:return json.loads(_row(r,"detail") or "{}")
    except Exception:return {}
async def _remember(db,uid,kind,iid):
    p=json.dumps({"kind":kind,"id":iid,"detail":{}},ensure_ascii=False);await db.prepare("INSERT INTO natural_events(user_id,event_type,target_id,detail) VALUES(?,'context',?,?)").bind(uid,iid,p).run()

async def handle_reference(db,token,message):
    chat=(message.get("chat") or {}).get("id");text=(message.get("text") or "").strip();n=_norm(text)
    if not chat:return False
    uid=await _uid(db,int(chat))
    if not uid:return False
    ctx=await _ctx(db,uid);ctx_id=ctx.get("id")

    if any(x in n for x in ("essa nao a outra","esse nao o outro","nao essa a outra","nao esse o outro")) and ctx_id:
        current=await db.prepare("SELECT kind FROM daily_items WHERE id=? AND user_id=?").bind(ctx_id,uid).first();kind=_row(current,"kind")
        rs=await _rows(db.prepare("SELECT id,kind,title,due_date,due_time FROM daily_items WHERE user_id=? AND status='pendente' AND id!=? AND kind=? ORDER BY due_date,due_time,id DESC LIMIT 5").bind(uid,ctx_id,kind))
        if len(rs)==1:
            r=rs[0];await _remember(db,uid,_row(r,"kind"),int(_row(r,"id")));await send_message(token,int(chat),f"Certo, então estamos falando de #{_row(r,'id')} {_row(r,'title')}. Continue.",reply_markup=_kb(MAIN_KB));return True
        if rs:
            await send_message(token,int(chat),"Tenho mais de uma 'outra'. Escolha pelo número:\n"+"\n".join(f"• #{_row(r,'id')} {_row(r,'title')}" for r in rs),reply_markup=_kb(MAIN_KB));return True

    if "proxima semana" in n and any(x in n for x in ("passa","joga","adia","adiar")) and ctx_id:
        r=await db.prepare("SELECT id,kind,title,due_date,due_time FROM daily_items WHERE id=? AND user_id=?").bind(ctx_id,uid).first()
        if r:
            try:
                base=datetime.fromisoformat(_row(r,"due_date")).date() if _row(r,"due_date") else _now().date()
            except Exception:base=_now().date()
            d=base+timedelta(days=7)
            await db.prepare("UPDATE daily_items SET due_date=?,status='pendente',postpone_count=postpone_count+1 WHERE id=? AND user_id=?").bind(d.isoformat(),ctx_id,uid).run()
            await send_message(token,int(chat),f"⏰ {_row(r,'title')} foi para {d.strftime('%d/%m')}"+(f" às {_row(r,'due_time')}" if _row(r,"due_time") else "")+". Semana que vem ganhou mais um problema. 😌",reply_markup=_kb(MAIN_KB));return True

    if "cancela" in n or "cancelar" in n:
        d=parse_date(text,_now().date());tm=parse_time(text)
        if d and tm and any(x in n for x in ("o que marquei","o compromisso","a tarefa","o que eu marquei")):
            rs=await _rows(db.prepare("SELECT id,kind,title FROM daily_items WHERE user_id=? AND status='pendente' AND due_date=? AND due_time=?").bind(uid,d.isoformat(),tm))
            if len(rs)==1:
                r=rs[0];await db.prepare("UPDATE daily_items SET status='cancelado',cancelled_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?").bind(_row(r,"id"),uid).run();await _remember(db,uid,_row(r,"kind"),int(_row(r,"id")));await send_message(token,int(chat),f"🚫 {_row(r,'title')} cancelado. Era o item de {d.strftime('%d/%m')} às {tm}.",reply_markup=_kb(MAIN_KB));return True
            if len(rs)>1:
                await send_message(token,int(chat),"Tem mais de uma coisa nesse horário. Escolha pelo #ID:\n"+"\n".join(f"• #{_row(r,'id')} {_row(r,'title')}" for r in rs),reply_markup=_kb(MAIN_KB));return True
    return False
