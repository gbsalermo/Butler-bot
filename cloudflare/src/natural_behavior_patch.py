import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

import app
import routine_integration
from nlu import parse_date, parse_time, validate_future
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
MAIN_KB = [["🌙 Day-off"],["➕ Adicionar","🗓️ Hoje"],["🛒 Item faltando","📚 Matérias"],["🏠 Cotidiano","🏋️ Musculação"]]


def _norm(text):
    v=unicodedata.normalize("NFKD",(text or "").lower());v="".join(c for c in v if not unicodedata.combining(c));return re.sub(r"\s+"," ",v).strip()

def _row(row,key,default=None):
    if row is None:return default
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default

async def _rows(stmt):
    r=await stmt.all();data=getattr(r,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []

def _kb(rows):return {"keyboard":rows,"resize_keyboard":True}
def _now():return datetime.now(timezone.utc).astimezone(LOCAL_TZ)

async def _uid(db,chat):
    r=await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat).first();return int(_row(r,"id")) if r else None

async def _remember(db,uid,kind,iid):
    payload=json.dumps({"kind":kind,"id":iid,"detail":{}},ensure_ascii=False)
    await db.prepare("INSERT INTO natural_events(user_id,event_type,target_id,detail) VALUES(?,'context',?,?)").bind(uid,iid,payload).run()

async def handle_explicit_simple_reminder(db,token,message):
    chat=(message.get("chat") or {}).get("id");text=(message.get("text") or "").strip();n=_norm(text)
    if not chat:return False

    # Pedido explícito de ação vence o assunto da frase. Assim, termos como
    # "jogos", "filmes" ou "receita" dentro da descrição nunca desviam um
    # "cria um lembrete..." para a biblioteca temática.
    direct=bool(re.match(
        r"^(?:butler[, ]+)?(?:por favor\s+)?(?:cria|crie|criar|adiciona|adicione|adicionar|faz|faca|fazer|coloca|coloque|anota|anote)\s+(?:(?:um|uma)\s+)?(?:lembrete|tarefa)\b",
        n,
    ))
    conversational=bool(re.match(r"^(?:butler[, ]+)?(?:so\s+)?(?:me\s+)?(?:avisa|avise|lembra|lembre)",n))
    simple=direct or (conversational and ("me avisa" in n or "me avise" in n or "so me lembra" in n or " de que " in f" {n} " or " lembra que " in f" {n} "))
    if not simple:return False

    d=parse_date(text,_now().date());tm=parse_time(text)
    if not d or not tm:return False
    ok,msg=validate_future(d,tm,_now().replace(tzinfo=None))
    if not ok:
        await send_message(token,int(chat),msg,reply_markup=_kb(MAIN_KB));return True
    uid=await _uid(db,int(chat))
    if not uid:return False
    title=text
    m=re.search(r"\bde\s+que\s+(.+)$",text,re.I)
    if m:title=m.group(1).strip()
    else:
        title=re.sub(r"^(?:Butler[,!:\-]?\s*)?(?:por\s+favor\s+)?(?:(?:só\s+)?(?:me\s+)?(?:avisa|avise|lembra|lembre)(?:-me)?|(?:cria|crie|criar|adiciona|adicione|adicionar|faz|faça|fazer|coloca|coloque|anota|anote)\s+(?:(?:um|uma)\s+)?(?:lembrete|tarefa)(?:\s+(?:para|pra))?)\s*","",title,flags=re.I)
        title=re.sub(r"\b(?:hoje|amanhã|amanha)\b","",title,flags=re.I)
        title=re.sub(r"(?:às|as)\s*\d{1,2}(?::\d{2}|h\d{0,2})?","",title,flags=re.I).strip(" ,.-")
    r=await db.prepare("INSERT INTO daily_items(user_id,kind,title,details,due_date,due_time,status) VALUES(?,'tarefa',?,'simple_reminder',?,?,'pendente') RETURNING id").bind(uid,title or "lembrete",d.isoformat(),tm).first()
    iid=int(_row(r,"id"));await _remember(db,uid,"lembrete",iid)
    await send_message(token,int(chat),f"🔔 Beleza. Te aviso em {d.strftime('%d/%m')} às {tm}: {title}. É só lembrete; depois do aviso ele vai para o histórico, não para a pilha de pendências.",reply_markup=_kb(MAIN_KB));return True

async def remember_after_message(db,message):
    chat=(message.get("chat") or {}).get("id");text=(message.get("text") or "").strip();n=_norm(text)
    if not chat:return
    creation=any(x in n for x in ("me lembra","cria um lembrete","crie um lembrete","adiciona um lembrete","adicione um lembrete","cria uma tarefa","crie uma tarefa","adiciona uma tarefa","adicione uma tarefa","tenho dentista","tenho consulta","tenho reuniao","tenho prova","marca compromisso","anota compromisso"))
    if not creation:return
    uid=await _uid(db,int(chat))
    if not uid:return
    r=await db.prepare("SELECT id,kind FROM daily_items WHERE user_id=? ORDER BY id DESC LIMIT 1").bind(uid).first()
    if r:await _remember(db,uid,_row(r,"kind"),int(_row(r,"id")))

async def _weekly_done(db,rid,target):
    start=target-timedelta(days=target.weekday());end=start+timedelta(days=6)
    r=await db.prepare("SELECT COUNT(*) n FROM routine_logs WHERE routine_id=? AND log_date BETWEEN ? AND ? AND status='feito'").bind(rid,start.isoformat(),end.isoformat()).first();return int(_row(r,"n",0))

def install_recurrence_patch():
    original_applies=routine_integration._applies
    original_scheduler=app.scheduled_tick

    def applies(weekdays,target):
        n=_norm(weekdays or "todos os dias")
        if re.search(r"\b\d+x por semana\b",n) or re.search(r"\ba cada \d+ dias?\b",n):return True
        return original_applies(weekdays,target)
    routine_integration._applies=applies

    async def scheduler(db,token):
        now=_now();today=now.date();clock=now.strftime('%H:%M')
        rs=await _rows(db.prepare("SELECT r.id,r.user_id,r.time_hhmm,r.weekdays,r.created_at FROM routines r WHERE r.active=1 AND r.time_hhmm IS NOT NULL"))
        for r in rs:
            n=_norm(_row(r,"weekdays") or "")
            suppress=False
            q=re.search(r"(\d+)x por semana",n)
            if q and await _weekly_done(db,int(_row(r,"id")),today)>=int(q.group(1)):suppress=True
            every=re.search(r"a cada (\d+) dias?",n)
            if every:
                try:
                    created=date.fromisoformat((_row(r,"created_at") or "")[:10]);suppress=((today-created).days%int(every.group(1))!=0)
                except Exception:pass
            if suppress:
                for t in routine_integration._times(_row(r,"time_hhmm")):
                    if t==clock:
                        key=f"routine:{_row(r,'id')}:{today.isoformat()}:{t}"
                        await db.prepare("INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(_row(r,"user_id"),key).run()
        await original_scheduler(db,token)
    app.scheduled_tick=scheduler
