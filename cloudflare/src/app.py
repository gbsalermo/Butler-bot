import io
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

from pypdf import PdfReader

from nlu import interpret, parse_date, parse_time, validate_future
from owner_profile import DEFAULT_FINANCE_LIMITS, OWNER_SUBJECTS, is_owner, preferred_name_for
from settings import UTC_OFFSET_HOURS, MORNING_SUMMARY_HOUR, MORNING_SUMMARY_MINUTE, WEEKLY_SUMMARY_WEEKDAY, WEEKLY_SUMMARY_HOUR, WEEKLY_SUMMARY_MINUTE
from telegram_api import get_file_bytes, send_message

try:
    from protocol_mass_data import WEEKS, SUBSTITUTIONS
except Exception:
    WEEKS, SUBSTITUTIONS = {}, {}

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
WEEKDAY_NAMES = ["segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado","domingo"]

MAIN_KB = [["🌙 Day-off"],["➕ Adicionar","🗓️ Hoje"],["🛒 Item faltando","📚 Matérias"],["🏠 Cotidiano","🏋️ Musculação"]]
COTIDIANO_KB = [["✅ Tarefas","📅 Compromissos"],["🛒 O que está faltando?","➕ Item faltando"],["🎯 Metas","🧘 Rotinas"],["💰 Finanças","👤 Como me chamar"],["🏠 Menu principal"]]
ACADEMIC_KB = [["📚 Minhas matérias","⚙️ Gerenciar matérias"],["📥 Importar grade por PDF/texto"],["🏠 Menu principal"]]
MANAGE_SUBJECT_KB = [["➕ Adicionar matéria","✏️ Editar matéria"],["🚫 Trancar matéria","🗑️ Remover matéria"],["⬅️ Voltar às matérias"]]
AGENDA_KB = [["⏭️ Amanhã","📆 Outra data"],["🗓️ Próximos 7 dias","📚 Histórico"],["🏠 Menu principal"]]
GROCERY_KB = [["➕ Adicionar item","📋 Ver itens faltando"],["🏠 Menu principal"]]
GOALS_KB = [["✅ Registrar progresso","🔥 Sequências"],["⬅️ Voltar ao cotidiano"]]
FINANCE_KB = [["➕ Entrada","➖ Gasto"],["📊 Resumo do mês","📈 Histórico"],["⬅️ Voltar ao cotidiano"]]
WORKOUT_KB = [["🚀 Começar os trabalhos","📅 Treino de hoje"],["📝 Registrar série","🔁 Substituir exercício"],["✅ Finalizar treino","😕 Não consegui treinar hoje"],["📈 Progresso","🔄 Reiniciar treinos"],["📥 Importar treino por PDF/texto"],["🏠 Menu principal"]]
CANCEL_KB = [["❌ Cancelar ação"]]


def kb(rows): return {"keyboard": rows, "resize_keyboard": True}
def now_local(): return datetime.now(timezone.utc).astimezone(LOCAL_TZ)
def norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower()); value="".join(ch for ch in value if not unicodedata.combining(ch)); return re.sub(r"[^a-z0-9 ]+"," ",value).strip()
def money(v): return (f"R$ {float(v):,.2f}").replace(",","X").replace(".",",").replace("X",".")
def rowget(row,key,default=None):
    if row is None:return default
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default
async def rows(stmt):
    result=await stmt.all(); data=getattr(result,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []

async def set_state(db,user_id,state=None,payload=None):
    await db.prepare("INSERT INTO user_sessions(user_id,state,payload,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET state=excluded.state,payload=excluded.payload,updated_at=CURRENT_TIMESTAMP").bind(user_id,state,json.dumps(payload or {},ensure_ascii=False)).run()
async def get_state(db,user_id):
    r=await db.prepare("SELECT state,payload FROM user_sessions WHERE user_id=?").bind(user_id).first()
    if not r:return None,{}
    try:p=json.loads(rowget(r,"payload") or "{}")
    except Exception:p={}
    return rowget(r,"state"),p
async def clear_state(db,user_id): await set_state(db,user_id,None,{})

async def ensure_user(db,chat_id,user):
    existing=await db.prepare("SELECT id,preferred_name,is_owner FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    owner=1 if is_owner(chat_id) else 0
    preferred=preferred_name_for(chat_id,user.get("first_name")) if owner else (rowget(existing,"preferred_name") if existing else None)
    await db.prepare("""INSERT INTO users(telegram_chat_id,telegram_user_id,preferred_name,first_name,username,is_owner)
    VALUES(?,?,?,?,?,?) ON CONFLICT(telegram_chat_id) DO UPDATE SET telegram_user_id=excluded.telegram_user_id,first_name=excluded.first_name,username=excluded.username,is_owner=excluded.is_owner,updated_at=CURRENT_TIMESTAMP""").bind(chat_id,user.get("id"),preferred,user.get("first_name"),user.get("username"),owner).run()
    r=await db.prepare("SELECT id,preferred_name FROM users WHERE telegram_chat_id=?").bind(chat_id).first(); uid=int(rowget(r,"id"))
    await db.prepare("INSERT OR IGNORE INTO assistant_state(user_id,day_off) VALUES(?,0)").bind(uid).run()
    await db.prepare("INSERT OR IGNORE INTO user_sessions(user_id,state,payload) VALUES(?,NULL,'{}')").bind(uid).run()
    for c,l in DEFAULT_FINANCE_LIMITS.items():await db.prepare("INSERT OR IGNORE INTO finance_limits(user_id,category,monthly_limit) VALUES(?,?,?)").bind(uid,c,l).run()
    for name in ("Inglês","Programação","Água","Alimentação","Musculação"):
        await db.prepare("INSERT INTO goals(user_id,name,category,active) SELECT ?,?,?,1 WHERE NOT EXISTS(SELECT 1 FROM goals WHERE user_id=? AND lower(name)=lower(?))").bind(uid,name,name.lower(),uid,name).run()
    if owner: await seed_owner(db,uid)
    return uid, existing is None, rowget(r,"preferred_name")

async def seed_owner(db,user_id):
    for it in OWNER_SUBJECTS:
        await db.prepare("INSERT OR IGNORE INTO subjects(user_id,name) VALUES(?,?)").bind(user_id,it["name"]).run()
        s=await db.prepare("SELECT id FROM subjects WHERE user_id=? AND name=?").bind(user_id,it["name"]).first()
        sid=int(rowget(s,"id"))
        e=await db.prepare("SELECT id FROM subject_sessions WHERE subject_id=? AND weekday=? AND start_time=? AND end_time=? AND COALESCE(location,'')=?").bind(sid,it["weekday"],it["start"],it["end"],it["location"]).first()
        if not e:await db.prepare("INSERT INTO subject_sessions(subject_id,weekday,start_time,end_time,location) VALUES(?,?,?,?,?)").bind(sid,it["weekday"],it["start"],it["end"],it["location"]).run()
    await db.prepare("INSERT OR IGNORE INTO protocol_mass_state(user_id,current_week,active) VALUES(?,1,0)").bind(user_id).run()

async def send(token,chat,text,keyboard=None): return await send_message(token,chat,text,reply_markup=kb(keyboard) if keyboard else None)

async def menu(token,chat,name):
    await send(token,chat,f"🕴️ Fala daí, {name or 'chefe'}?",MAIN_KB)

async def list_subjects_text(db,uid):
    rs=await rows(db.prepare("""SELECT s.name,s.active,ss.weekday,ss.start_time,ss.end_time,ss.location FROM subjects s LEFT JOIN subject_sessions ss ON ss.subject_id=s.id WHERE s.user_id=? ORDER BY s.name,ss.weekday,ss.start_time""").bind(uid))
    if not rs:return "📚 Nenhuma matéria cadastrada ainda."
    out=["📚 Suas matérias:"]
    current=None
    for r in rs:
        name=rowget(r,"name"); active=int(rowget(r,"active",1))
        if name!=current:out.append(f"\n{'📘' if active else '🔒'} {name}"); current=name
        if rowget(r,"weekday"):out.append(f"• {rowget(r,'weekday').capitalize()} {rowget(r,'start_time')}–{rowget(r,'end_time')} — {rowget(r,'location') or 'local não informado'}")
    return "\n".join(out)

async def agenda_text(db,uid,target,include_overdue=False):
    wd=WEEKDAY_NAMES[target.weekday()]
    out=[f"🗓️ {wd.capitalize()}, {target.strftime('%d/%m/%Y')}"]
    ss=await rows(db.prepare("""SELECT s.name,ss.start_time,ss.end_time,ss.location FROM subjects s JOIN subject_sessions ss ON ss.subject_id=s.id WHERE s.user_id=? AND s.active=1 AND ss.weekday=? ORDER BY ss.start_time""").bind(uid,wd))
    items=await rows(db.prepare("SELECT kind,title,due_time,status FROM daily_items WHERE user_id=? AND due_date=? AND status!='cancelado' ORDER BY COALESCE(due_time,'99:99')").bind(uid,target.isoformat()))
    if ss:
        out.append("\n🎓 Aulas")
        for r in ss:out.append(f"• {rowget(r,'start_time')} — {rowget(r,'name')} ({rowget(r,'location') or 'local não informado'})")
    if items:
        out.append("\n📋 Agenda")
        for r in items:
            icon="✅" if rowget(r,"kind")=="tarefa" else "📅"; tm=f"{rowget(r,'due_time')} — " if rowget(r,"due_time") else ""
            status=" ✅" if rowget(r,"status")=="concluido" else ""
            out.append(f"• {icon} {tm}{rowget(r,'title')}{status}")
    if include_overdue:
        overdue=await rows(db.prepare("SELECT title,due_date FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente' AND due_date<? ORDER BY due_date").bind(uid,target.isoformat()))
        if overdue:
            out.append("\n📌 Pendências")
            for r in overdue:out.append(f"• {rowget(r,'title')} — venceu em {rowget(r,'due_date')[8:10]}/{rowget(r,'due_date')[5:7]}")
    if not ss and not items:out.append("\nNada marcado. Um raro espaço em branco no calendário.")
    return "\n".join(out)

async def grocery_text(db,uid):
    rs=await rows(db.prepare("SELECT name,quantity,note FROM grocery_items WHERE user_id=? AND missing=1 ORDER BY name").bind(uid))
    if not rs:return "🛒 Não há nada marcado como faltando em casa."
    return "🛒 Está faltando:\n"+"\n".join(f"• {rowget(r,'name')}{' — '+rowget(r,'quantity') if rowget(r,'quantity') else ''}" for r in rs)

async def tasks_text(db,uid,kind=None):
    sql="SELECT id,kind,title,due_date,due_time,status,postpone_count FROM daily_items WHERE user_id=?"; params=[uid]
    if kind:sql+=" AND kind=?";params.append(kind)
    sql+=" ORDER BY CASE status WHEN 'pendente' THEN 0 WHEN 'concluido' THEN 1 ELSE 2 END,due_date DESC,id DESC LIMIT 30"
    rs=await rows(db.prepare(sql).bind(*params))
    if not rs:return "Nada por aqui. Suspeitamente tranquilo."
    out=[]
    for r in rs:
        st={"pendente":"⏳","concluido":"✅","cancelado":"🚫"}.get(rowget(r,"status"),"•"); when=""
        if rowget(r,"due_date"):when=f" — {rowget(r,'due_date')[8:10]}/{rowget(r,'due_date')[5:7]}"+(f" {rowget(r,'due_time')}" if rowget(r,"due_time") else "")
        out.append(f"{st} #{rowget(r,'id')} {rowget(r,'title')}{when}")
    return "\n".join(out)

async def finance_report(db,uid):
    prefix=now_local().strftime("%Y-%m")
    rs=await rows(db.prepare("SELECT kind,category,SUM(amount) total FROM finance_entries WHERE user_id=? AND occurred_on LIKE ? GROUP BY kind,category").bind(uid,prefix+"%"))
    if not rs:return "📊 Você quer relatório financeiro sem ter me contado para onde o dinheiro foi. Ambicioso. Cadastre entradas e saídas primeiro; eu ainda não leio extrato por telepatia."
    inc=sum(float(rowget(r,"total",0)) for r in rs if rowget(r,"kind")=="entrada"); exp=sum(float(rowget(r,"total",0)) for r in rs if rowget(r,"kind")=="saida")
    out=["📊 Relatório do mês",f"💰 Entradas: {money(inc)}",f"💸 Saídas: {money(exp)}",f"🏦 Saldo registrado: {money(inc-exp)}"]
    cats={rowget(r,"category"):float(rowget(r,"total",0)) for r in rs if rowget(r,"kind")=="saida"}
    if cats:out.append("\nPor categoria:");out.extend(f"• {c.title()}: {money(v)}" for c,v in sorted(cats.items(),key=lambda x:x[1],reverse=True))
    limits=await rows(db.prepare("SELECT category,monthly_limit FROM finance_limits WHERE user_id=?").bind(uid)); lm={rowget(r,"category"):float(rowget(r,"monthly_limit")) for r in limits}
    alerts=[(c,v,lm[c]) for c,v in cats.items() if c in lm and v>lm[c]]
    if alerts:out.append("\n🚨 Alertas:");out.extend(f"• {c.title()}: {money(v)} / {money(l)}. A categoria pediu liberdade e você deu independência financeira." for c,v,l in alerts)
    out.append("\nIsso é o que eu consigo provar com o que você registrou. A parte chata continua sendo me contar quando o dinheiro entra e, principalmente, quando foge. 😌")
    return "\n".join(out)

async def streaks_text(db,uid):
    today=now_local().date(); names=[("🇬🇧","Inglês"),("💻","Programação"),("💧","Água"),("🥗","Alimentação"),("🏋️","Musculação")]
    out=["🔥 Sequências\nUm pouco de pressão visual. Porque aparentemente funciona."]
    for icon,name in names:
        if name=="Musculação":
            rr=await rows(db.prepare("SELECT workout_date d FROM workout_logs WHERE user_id=? AND status='feito' UNION SELECT training_date d FROM protocol_mass_sessions WHERE user_id=? AND completed_at IS NOT NULL ORDER BY d").bind(uid,uid))
        else:
            g=await db.prepare("SELECT id FROM goals WHERE user_id=? AND lower(name)=lower(?) LIMIT 1").bind(uid,name).first(); gid=rowget(g,"id")
            rr=await rows(db.prepare("SELECT DISTINCT log_date d FROM goal_progress WHERE goal_id=? ORDER BY d").bind(gid)) if gid else []
        ds=sorted({date.fromisoformat(rowget(r,"d")) for r in rr if rowget(r,"d")})
        s=set(ds); cur=0; d=today if today in s else today-timedelta(days=1)
        while d in s:cur+=1;d-=timedelta(days=1)
        best=0;run=0;prev=None
        for x in ds:
            if prev and x==prev+timedelta(days=1):run+=1
            else:run=1
            best=max(best,run);prev=x
        marks="".join("🟩" if today-timedelta(days=i) in s else "⬜" for i in reversed(range(7)))
        out.append(f"\n{icon} {name}\n{marks}\nAtual: {cur} dia(s) 🔥 • Recorde: {best} • Total: {len(ds)}")
    return "\n".join(out)

async def workout_plan(db,uid,owner,target=None):
    target=target or now_local().date(); wd=WEEKDAY_NAMES[target.weekday()]
    if owner and WEEKS:
        st=await db.prepare("SELECT current_week,active FROM protocol_mass_state WHERE user_id=?").bind(uid).first(); week=int(rowget(st,"current_week",1)); active=int(rowget(st,"active",0))
        exercises=WEEKS.get(str(week),{}).get(wd,[])
        return wd,week,active,[{"name":e.get("name"),"sets":e.get("series"),"load":None,"reps":None,"raw":e} for e in exercises]
    day=await db.prepare("SELECT id,focus FROM workout_days WHERE user_id=? AND weekday=?").bind(uid,wd).first()
    if not day:return wd,None,1,[]
    ex=await rows(db.prepare("SELECT name,sets,reps,load FROM workout_exercises WHERE workout_day_id=? ORDER BY position,id").bind(rowget(day,"id")))
    return wd,None,1,[{"name":rowget(r,"name"),"sets":rowget(r,"sets"),"reps":rowget(r,"reps"),"load":rowget(r,"load"),"raw":None} for r in ex]

async def workout_text(db,uid,owner):
    wd,week,active,ex=await workout_plan(db,uid,owner)
    if owner and not active:return "🏋️ Os trabalhos ainda não começaram. Use 🚀 Começar os trabalhos quando quiser iniciar as 12 semanas."
    if not ex:return f"🏋️ Não há treino cadastrado para {wd}."
    out=[f"🏋️ Treino de {wd.capitalize()}"+(f" — semana {week}/12" if week else "")]
    for i,e in enumerate(ex,1):
        scheme=e.get("sets") or ""; extra=[]
        if e.get("reps"):extra.append(str(e["reps"]));
        if e.get("load"):extra.append(str(e["load"]));
        suffix=(" — "+" • ".join(extra)) if extra else ""
        out.append(f"{i}. {e['name']} — {scheme}{suffix}")
    return "\n".join(out)

async def history_day(db,uid,target):
    text=await agenda_text(db,uid,target,False); out=[f"📖 Histórico — {target.strftime('%d/%m/%Y')}",text.split("\n",1)[1] if "\n" in text else text]
    rr=await rows(db.prepare("SELECT r.name FROM routines r JOIN routine_logs l ON l.routine_id=r.id WHERE r.user_id=? AND l.log_date=? AND l.status='feito'").bind(uid,target.isoformat()))
    if rr:out.append("\n🧘 Rotinas registradas\n"+"\n".join(f"• ✅ {rowget(r,'name')}" for r in rr))
    w=await db.prepare("SELECT status,reason FROM workout_logs WHERE user_id=? AND workout_date=?").bind(uid,target.isoformat()).first()
    if w:out.append(f"\n🏋️ Academia: {'✅ feito' if rowget(w,'status')=='feito' else '➖ não realizado'}"+(f" — {rowget(w,'reason')}" if rowget(w,'reason') else ""))
    return "\n".join(out)

async def parse_text_file(data,filename):
    if filename.lower().endswith(".pdf"):
        reader=PdfReader(io.BytesIO(data));return "\n".join((p.extract_text() or "") for p in reader.pages)
    return data.decode("utf-8",errors="replace")

def parse_workout_text(text):
    aliases={"segunda":"segunda-feira","segunda feira":"segunda-feira","terca":"terça-feira","terça":"terça-feira","quarta":"quarta-feira","quinta":"quinta-feira","sexta":"sexta-feira","sabado":"sábado","sábado":"sábado","domingo":"domingo"}
    day=None;focus="Treino";out=[]
    for raw in text.splitlines():
        line=re.sub(r"\s+"," ",raw).strip(" •-–—\t")
        if not line:continue
        n=norm(line)
        found=False
        for a,d in aliases.items():
            if n==a or n.startswith(a+" "):
                day=d;rest=n[len(a):].strip();focus=(re.sub(r"^(treino|foco)\s+","",rest).strip().title() or "Treino");found=True;break
        if found:continue
        if not day:continue
        m=re.search(r"\b(\d{1,2})\s*[xX×]\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?|ate falha|falha)\b",line,re.I)
        if not m:continue
        name=line[:m.start()].strip(" |;-–—");after=line[m.end():].strip(" |;-–—")
        if name:out.append({"weekday":day,"focus":focus,"name":name,"sets":int(m.group(1)),"reps":m.group(2).replace("–","-"),"load":after or None})
    return out

def parse_schedule_text(text):
    # Extrator conservador para linhas com nome + código SIGAA + local opcional.
    result=[]
    daymap={"2":"segunda-feira","3":"terça-feira","4":"quarta-feira","5":"quinta-feira","6":"sexta-feira","7":"sábado"}
    blocks={"M":{"1":("07:00","08:00"),"2":("08:00","09:00"),"3":("09:00","10:00"),"4":("10:00","11:00"),"5":("11:00","12:00")},"T":{"1":("13:00","14:00"),"2":("14:00","15:00"),"3":("15:00","16:00"),"4":("16:00","17:00"),"5":("17:00","18:00")},"N":{"1":("18:00","19:00"),"2":("19:00","20:00"),"3":("20:00","21:00"),"4":("21:00","22:00")}}
    for raw in text.splitlines():
        line=re.sub(r"\s+"," ",raw).strip()
        m=re.search(r"\b([2-7]+)([MTN])(\d+)\b",line)
        if not m:continue
        code=m.group(0);name=line[:m.start()].strip(" -–—|;:") or "Matéria";tail=line[m.end():].strip(" -–—|;:")
        period=m.group(2);slots=m.group(3)
        if not slots:continue
        start=blocks.get(period,{}).get(slots[0],(None,None))[0];end=blocks.get(period,{}).get(slots[-1],(None,None))[1]
        if not start or not end:continue
        for d in m.group(1):result.append({"name":name,"weekday":daymap[d],"start":start,"end":end,"location":tail or None,"code":code})
    return result

async def handle_natural(db,token,chat,uid,owner,text):
    intent=interpret(text,now_local().date())
    if not intent:return False
    name,data=intent
    if name=="grocery_query":await send(token,chat,await grocery_text(db,uid),GROCERY_KB);return True
    if name=="grocery_add":
        for item in data.get("items",[]):await db.prepare("INSERT INTO grocery_items(user_id,name,missing) VALUES(?,?,1) ON CONFLICT(user_id,name) DO UPDATE SET missing=1,updated_at=CURRENT_TIMESTAMP").bind(uid,item).run()
        await send(token,chat,"🛒 Anotado: "+", ".join(data.get("items",[]))+". Pelo menos a memória agora é problema meu.",GROCERY_KB);return True
    if name=="grocery_bought":
        target=data.get("target","");rs=await rows(db.prepare("SELECT id,name FROM grocery_items WHERE user_id=? AND missing=1").bind(uid));matches=[r for r in rs if norm(target) in norm(rowget(r,"name")) or norm(rowget(r,"name")) in norm(target)]
        if len(matches)==1:
            await db.prepare("UPDATE grocery_items SET missing=0,updated_at=CURRENT_TIMESTAMP WHERE id=?").bind(rowget(matches[0],"id")).run();await send(token,chat,f"✅ {rowget(matches[0],'name')} saiu da lista. Milagre logístico registrado.",GROCERY_KB)
        else:await send(token,chat,"Não achei um único item claro para marcar como comprado. Use o nome como aparece na lista.",GROCERY_KB)
        return True
    if name in ("agenda_query","agenda_range"):
        if name=="agenda_range":
            parts=[]
            for i in range(1,8):parts.append(await agenda_text(db,uid,now_local().date()+timedelta(days=i)))
            await send(token,chat,"\n\n".join(parts),AGENDA_KB)
        else:await send(token,chat,await agenda_text(db,uid,data.get("date") or now_local().date(),True),AGENDA_KB)
        return True
    if name=="overdue_query":
        rs=await rows(db.prepare("SELECT id,title,due_date FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente' AND due_date<? ORDER BY due_date").bind(uid,now_local().date().isoformat()));await send(token,chat,"📌 Pendências:\n"+("\n".join(f"• #{rowget(r,'id')} {rowget(r,'title')} — {rowget(r,'due_date')}" for r in rs) if rs else "Nenhuma. Estranhamente civilizado."),COTIDIANO_KB);return True
    if name=="finance_report":await send(token,chat,await finance_report(db,uid),FINANCE_KB);return True
    if name=="finance_add":
        desc=data.get("description") or "Outros";n=norm(desc);cat="outros"
        if any(x in n for x in ("mercado","lanche","comida","restaurante")):cat="alimentação"
        elif any(x in n for x in ("uber","onibus","gasolina","transporte")):cat="transporte"
        elif any(x in n for x in ("cinema","jogo","lazer")):cat="lazer"
        elif any(x in n for x in ("roupa","shopee","compra")):cat="compras"
        elif data["kind"]=="entrada":cat="renda"
        await db.prepare("INSERT INTO finance_entries(user_id,kind,amount,category,description,occurred_on) VALUES(?,?,?,?,?,?)").bind(uid,data["kind"],data["amount"],cat,desc,now_local().date().isoformat()).run();await send(token,chat,(f"💸 {money(data['amount'])} saiu. Tô vendo dinheiro correr com uma disposição física impressionante. 😏" if data["kind"]=="saida" else f"💰 {money(data['amount'])} entrou. Finalmente uma seta apontando na direção agradável."),FINANCE_KB);return True
    if name in ("task_create","appointment_create"):
        kind="tarefa" if name=="task_create" else "compromisso";title=data.get("title") or "";d=data.get("date");tm=data.get("time")
        if data.get("reminder_request") and (not d or not tm):await set_state(db,uid,"natural_when",{"kind":kind,"title":title});await send(token,chat,f"Entendi *{title}*. Só falta quando. Manda algo como `amanhã às 15h`.",CANCEL_KB);return True
        ok,msg=validate_future(d,tm,now_local().replace(tzinfo=None))
        if not ok:await send(token,chat,msg,MAIN_KB);return True
        await db.prepare("INSERT INTO daily_items(user_id,kind,title,due_date,due_time,status) VALUES(?,?,?,?,?,'pendente')").bind(uid,kind,title,d.isoformat() if d else None,tm).run();await send(token,chat,f"✅ {kind.capitalize()} salvo: {title}"+(f" — {d.strftime('%d/%m')}" if d else "")+(f" às {tm}" if tm else "")+". Eu lembro; executar continua sendo sua parte.",MAIN_KB);return True
    if name=="task_complete":
        target=data.get("target","");rs=await rows(db.prepare("SELECT id,title,postpone_count,due_date,due_time FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente'").bind(uid));matches=[r for r in rs if norm(target) in norm(rowget(r,"title")) or norm(rowget(r,"title")) in norm(target)]
        if len(matches)==1:
            r=matches[0];await db.prepare("UPDATE daily_items SET status='concluido',completed_at=CURRENT_TIMESTAMP WHERE id=?").bind(rowget(r,"id")).run();n=int(rowget(r,"postpone_count",0));comment=f" Resolvido depois de {n} adiamentos. Não vou dizer 'eu avisei'. Quase. 😌" if n>=2 else " Muito bem. Não espalha que eu disse isso.";await send(token,chat,"✅ "+rowget(r,"title")+" concluída."+comment,MAIN_KB)
        else:await send(token,chat,"Encontrei zero ou mais de uma tarefa parecida. Use `✅ Tarefas` e o número #ID para evitar que eu mate a tarefa errada.",COTIDIANO_KB)
        return True
    if name=="late_notice":
        target=data.get("target") or "";rs=await rows(db.prepare("SELECT id,title,due_time FROM daily_items WHERE user_id=? AND kind='compromisso' AND status='pendente' AND due_date>=? ORDER BY due_date,due_time").bind(uid,now_local().date().isoformat()));matches=[r for r in rs if not target or norm(target) in norm(rowget(r,"title"))]
        if len(matches)==1:
            r=matches[0];countrow=await db.prepare("SELECT COUNT(*) n FROM natural_events WHERE user_id=? AND event_type='late_notice'").bind(uid).first();count=int(rowget(countrow,"n",0))+1;await db.prepare("INSERT INTO natural_events(user_id,event_type,target_id,detail) VALUES(?,'late_notice',?,?)").bind(uid,rowget(r,"id"),rowget(r,"title")).run();msg="Vou registrar como caso isolado. Estou sendo generoso com a estatística. 😌" if count==1 else ("Segunda ocorrência. A palavra 'isolado' já está ficando difícil de defender. 👀" if count==2 else f"Com {count} avisos, isso já não chega a ser exatamente uma novidade. 😏");await send(token,chat,f"⏰ {rowget(r,'title')} {rowget(r,'due_time') or ''}. {msg}\nNão alterei o horário; só registrei o aviso.",MAIN_KB)
        else:await send(token,chat,"Qual compromisso? Não vou escolher um aleatoriamente só para poder te zoar.",MAIN_KB)
        return True
    if name=="workout_skip":
        st=await db.prepare("SELECT active,current_week FROM protocol_mass_state WHERE user_id=?").bind(uid).first() if owner else None
        if owner and (not st or not int(rowget(st,"active",0))):await send(token,chat,"Entendi. Mas os trabalhos ainda nem começaram oficialmente, então não vou contar falta antes da largada.",WORKOUT_KB);return True
        today=now_local().date();await db.prepare("INSERT INTO workout_logs(user_id,workout_date,weekday,status,reason) VALUES(?,?,?,'faltou',?) ON CONFLICT(user_id,workout_date) DO UPDATE SET status='faltou',reason=excluded.reason").bind(uid,today.isoformat(),WEEKDAY_NAMES[today.weekday()],data.get("reason")).run();await send(token,chat,"😕 Anotado. Um dia acontece. Dois começam uma conversa. Três viram estatística e eu fico insuportável.",WORKOUT_KB);return True
    return False

async def handle_state(db,token,chat,uid,owner,state,payload,message):
    text=(message.get("text") or "").strip()
    if text in ("❌ Cancelar ação","/cancelar"):
        await clear_state(db,uid);await send(token,chat,"Cancelado. Nada foi alterado.",MAIN_KB);return True
    if state=="ask_name":
        if not text:return True
        await db.prepare("UPDATE users SET preferred_name=? WHERE id=?").bind(text[:60],uid).run();await clear_state(db,uid);await send(token,chat,f"Fechado. Vou te chamar de {text[:60]}. Não abuse da intimidade.",MAIN_KB);return True
    if state in ("task_title","appointment_title"):
        if not text:return True
        payload["title"]=text;payload["kind"]="tarefa" if state=="task_title" else "compromisso";await set_state(db,uid,"item_date",payload);await send(token,chat,"Quando? Responda `hoje`, `amanhã`, `DD/MM` ou `sem data`.",CANCEL_KB);return True
    if state=="item_date":
        if norm(text)=="sem data":payload["date"]=None
        else:
            d=parse_date(text,now_local().date())
            if not d:await send(token,chat,"Não reconheci a data. Use `hoje`, `amanhã` ou `DD/MM`.",CANCEL_KB);return True
            payload["date"]=d.isoformat()
        await set_state(db,uid,"item_time",payload);await send(token,chat,"Horário? Ex.: `15h`, `15:30`. Se não houver, responda `sem horário`.",CANCEL_KB);return True
    if state=="item_time":
        tm=None if norm(text) in ("sem horario","sem hora") else parse_time(text)
        if not tm and norm(text) not in ("sem horario","sem hora"):await send(token,chat,"Não entendi o horário. Use `15h`, `15:30` ou `sem horário`.",CANCEL_KB);return True
        d=date.fromisoformat(payload["date"]) if payload.get("date") else None;ok,msg=validate_future(d,tm,now_local().replace(tzinfo=None))
        if not ok:await send(token,chat,msg,CANCEL_KB);return True
        await db.prepare("INSERT INTO daily_items(user_id,kind,title,due_date,due_time,status) VALUES(?,?,?,?,?,'pendente')").bind(uid,payload["kind"],payload["title"],payload.get("date"),tm).run();await clear_state(db,uid);await send(token,chat,f"✅ {payload['kind'].capitalize()} salva. Curto, objetivo e sem interrogatório policial.",MAIN_KB);return True
    if state=="grocery_add":
        items=[x.strip() for x in re.split(r",|\s+e\s+",re.sub(r"^falta\s+","",text,flags=re.I)) if x.strip()]
        for item in items:await db.prepare("INSERT INTO grocery_items(user_id,name,missing) VALUES(?,?,1) ON CONFLICT(user_id,name) DO UPDATE SET missing=1,updated_at=CURRENT_TIMESTAMP").bind(uid,item).run()
        await clear_state(db,uid);await send(token,chat,"🛒 Anotado: "+", ".join(items)+".",GROCERY_KB);return True
    if state=="agenda_date" or state=="history_date":
        d=parse_date(text,now_local().date())
        if not d:await send(token,chat,"Use `DD/MM`, `amanhã`, `sexta` etc.",CANCEL_KB);return True
        await clear_state(db,uid);await send(token,chat,await (history_day(db,uid,d) if state=="history_date" else agenda_text(db,uid,d,False)),AGENDA_KB);return True
    if state=="rename":
        await db.prepare("UPDATE users SET preferred_name=? WHERE id=?").bind(text[:60],uid).run();await clear_state(db,uid);await send(token,chat,f"Certo. {text[:60]} agora. Mudança registrada; crise de identidade evitada.",COTIDIANO_KB);return True
    if state=="goal_progress":
        g=await db.prepare("SELECT id,name FROM goals WHERE user_id=? AND lower(name)=lower(?)").bind(uid,text).first()
        if not g:await send(token,chat,"Escolha: Inglês, Programação, Água, Alimentação ou Musculação.",CANCEL_KB);return True
        await db.prepare("INSERT INTO goal_progress(goal_id,amount,log_date) VALUES(?,1,?)").bind(rowget(g,"id"),now_local().date().isoformat()).run();await clear_state(db,uid);await send(token,chat,f"🔥 {rowget(g,'name')} registrado hoje. Pequeno demais para discurso, importante demais para ignorar.",GOALS_KB);return True
    if state=="finance_amount":
        try:v=float(text.replace("R$"," ").replace(".","").replace(",",".").strip())
        except Exception:await send(token,chat,"Manda só o valor, tipo `35,90`.",CANCEL_KB);return True
        payload["amount"]=v;await set_state(db,uid,"finance_category",payload);await send(token,chat,"Categoria? Alimentação, Transporte, Lazer, Compras, Renda ou Outros.",CANCEL_KB);return True
    if state=="finance_category":
        payload["category"]=norm(text);await set_state(db,uid,"finance_desc",payload);await send(token,chat,"Descrição curta? Ou `-` para pular.",CANCEL_KB);return True
    if state=="finance_desc":
        desc=None if text=="-" else text;await db.prepare("INSERT INTO finance_entries(user_id,kind,amount,category,description,occurred_on) VALUES(?,?,?,?,?,?)").bind(uid,payload["kind"],payload["amount"],payload["category"],desc,now_local().date().isoformat()).run();await clear_state(db,uid);msg=f"💸 {money(payload['amount'])} saiu. Registrado. Tô vendo dinheiro sair e até agora nada de concreto. Adianta em que mesmo? 😏" if payload["kind"]=="saida" else f"💰 {money(payload['amount'])} entrou. Finalmente uma seta apontando na direção agradável.";await send(token,chat,msg,FINANCE_KB);return True
    if state=="natural_when":
        d=parse_date(text,now_local().date());tm=parse_time(text)
        if not d or not tm:await send(token,chat,"Preciso de dia e hora. Ex.: `amanhã às 15h`.",CANCEL_KB);return True
        ok,msg=validate_future(d,tm,now_local().replace(tzinfo=None))
        if not ok:await send(token,chat,msg,CANCEL_KB);return True
        await db.prepare("INSERT INTO daily_items(user_id,kind,title,due_date,due_time,status) VALUES(?,?,?,?,?,'pendente')").bind(uid,payload["kind"],payload["title"],d.isoformat(),tm).run();await clear_state(db,uid);await send(token,chat,f"✅ Fechado: {payload['title']} — {d.strftime('%d/%m')} às {tm}.",MAIN_KB);return True
    if state=="subject_add_name":
        payload["name"]=text;await set_state(db,uid,"subject_add_schedule",payload);await send(token,chat,"Manda `terça 14:00-16:00 | PAV II sala 05`.",CANCEL_KB);return True
    if state=="subject_add_schedule":
        m=re.match(r"(.+?)\s+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})(?:\s*\|\s*(.+))?$",text)
        if not m:await send(token,chat,"Formato: `terça 14:00-16:00 | sala 05`.",CANCEL_KB);return True
        wd=norm(m.group(1));mapd={norm(x):x for x in WEEKDAY_NAMES};weekday=mapd.get(wd)
        if not weekday:await send(token,chat,"Dia da semana não reconhecido.",CANCEL_KB);return True
        await db.prepare("INSERT OR IGNORE INTO subjects(user_id,name) VALUES(?,?)").bind(uid,payload["name"]).run();s=await db.prepare("SELECT id FROM subjects WHERE user_id=? AND name=?").bind(uid,payload["name"]).first();await db.prepare("INSERT INTO subject_sessions(subject_id,weekday,start_time,end_time,location) VALUES(?,?,?,?,?)").bind(rowget(s,"id"),weekday,m.group(2),m.group(3),m.group(4)).run();await clear_state(db,uid);await send(token,chat,"✅ Matéria adicionada.",ACADEMIC_KB);return True
    if state in ("subject_remove","subject_lock"):
        s=await db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND lower(name)=lower(?)").bind(uid,text).first()
        if not s:await send(token,chat,"Não achei essa matéria pelo nome exato.",CANCEL_KB);return True
        if state=="subject_remove":await db.prepare("DELETE FROM subjects WHERE id=?").bind(rowget(s,"id")).run()
        else:await db.prepare("UPDATE subjects SET active=0 WHERE id=?").bind(rowget(s,"id")).run()
        await clear_state(db,uid);await send(token,chat,"Feito. O histórico não vai escrever uma tese sobre isso.",ACADEMIC_KB);return True
    if state=="workout_skip_reason":
        today=now_local().date();await db.prepare("INSERT INTO workout_logs(user_id,workout_date,weekday,status,reason) VALUES(?,?,?,'faltou',?) ON CONFLICT(user_id,workout_date) DO UPDATE SET status='faltou',reason=excluded.reason").bind(uid,today.isoformat(),WEEKDAY_NAMES[today.weekday()],None if text=="-" else text).run();await clear_state(db,uid);await send(token,chat,"😕 Falta registrada. Acontece. Só não vamos transformar exceção em calendário.",WORKOUT_KB);return True
    if state=="workout_series_exercise":
        wd,week,active,ex=await workout_plan(db,uid,owner);idx=int(text)-1 if text.isdigit() else -1
        target=ex[idx]["name"] if 0<=idx<len(ex) else text;payload.update({"exercise":target,"week":week});await set_state(db,uid,"workout_series_data",payload);await send(token,chat,"Manda `40 kg | 10 reps`. Vou registrar a próxima série desse exercício.",CANCEL_KB);return True
    if state=="workout_series_data":
        parts=[x.strip() for x in text.split("|",1)];load=parts[0];reps=parts[1] if len(parts)>1 else None;today=now_local().date();table="protocol_mass_set_logs" if owner else "workout_set_logs"
        if owner:
            c=await db.prepare("SELECT COUNT(*) n FROM protocol_mass_set_logs WHERE user_id=? AND week=? AND weekday=? AND exercise_name=?").bind(uid,payload.get("week") or 1,WEEKDAY_NAMES[today.weekday()],payload["exercise"]).first();sn=int(rowget(c,"n",0))+1;await db.prepare("INSERT INTO protocol_mass_set_logs(user_id,week,weekday,exercise_name,set_number,load,reps) VALUES(?,?,?,?,?,?,?)").bind(uid,payload.get("week") or 1,WEEKDAY_NAMES[today.weekday()],payload["exercise"],sn,load,reps).run()
        else:
            c=await db.prepare("SELECT COUNT(*) n FROM workout_set_logs WHERE user_id=? AND workout_date=? AND exercise_name=?").bind(uid,today.isoformat(),payload["exercise"]).first();sn=int(rowget(c,"n",0))+1;await db.prepare("INSERT INTO workout_set_logs(user_id,workout_date,exercise_name,set_number,load,reps) VALUES(?,?,?,?,?,?)").bind(uid,today.isoformat(),payload["exercise"],sn,load,reps).run()
        await clear_state(db,uid);await send(token,chat,f"✅ {payload['exercise']} — série {sn} registrada. Eu vi a carga. Não vou elogiar cedo demais.",WORKOUT_KB);return True
    if state in ("import_schedule","import_workout"):
        doc=message.get("document")
        if not doc:await send(token,chat,"Estou esperando um PDF textual ou `.txt`. Imagem não entra direto.",CANCEL_KB);return True
        filename=doc.get("file_name") or "arquivo";mime=doc.get("mime_type") or ""
        if not (filename.lower().endswith((".pdf",".txt")) or mime in ("application/pdf","text/plain")):await send(token,chat,"Formato aceito: PDF com texto pesquisável ou `.txt`.",CANCEL_KB);return True
        try:data=await get_file_bytes(token,doc["file_id"]);content=await parse_text_file(data,filename)
        except Exception as exc:await send(token,chat,f"Não consegui ler o arquivo: {type(exc).__name__}. Se for scan/imagem, converta antes para PDF textual.",CANCEL_KB);return True
        parsed=parse_schedule_text(content) if state=="import_schedule" else parse_workout_text(content)
        if not parsed:await send(token,chat,"Li o arquivo, mas não encontrei dados com formato seguro para importar. Prefiro pedir clareza a inventar sua rotina.",CANCEL_KB);return True
        payload={"items":parsed,"kind":state};await set_state(db,uid,"import_confirm",payload);preview=[]
        if state=="import_schedule":preview=[f"• {x['name']} — {x['weekday']} {x['start']}–{x['end']} ({x['location'] or 'sem local'})" for x in parsed[:20]]
        else:preview=[f"• {x['weekday']} — {x['name']} — {x['sets']}x{x['reps']}{' — '+x['load'] if x['load'] else ''}" for x in parsed[:20]]
        await send(token,chat,"📥 Prévia:\n"+"\n".join(preview)+f"\n\nTotal: {len(parsed)}. Responda `confirmar` para substituir/importar ou cancele.",CANCEL_KB);return True
    if state=="import_confirm":
        if norm(text)!="confirmar":await send(token,chat,"Digite `confirmar` ou cancele.",CANCEL_KB);return True
        items=payload.get("items",[])
        if payload.get("kind")=="import_schedule":
            await db.prepare("DELETE FROM subject_sessions WHERE subject_id IN (SELECT id FROM subjects WHERE user_id=?)").bind(uid).run();await db.prepare("DELETE FROM subjects WHERE user_id=?").bind(uid).run()
            for x in items:
                await db.prepare("INSERT OR IGNORE INTO subjects(user_id,name) VALUES(?,?)").bind(uid,x["name"]).run();s=await db.prepare("SELECT id FROM subjects WHERE user_id=? AND name=?").bind(uid,x["name"]).first();await db.prepare("INSERT INTO subject_sessions(subject_id,weekday,start_time,end_time,location) VALUES(?,?,?,?,?)").bind(rowget(s,"id"),x["weekday"],x["start"],x["end"],x.get("location")).run()
            msg=f"✅ Grade importada: {len(items)} bloco(s)."
        else:
            await db.prepare("DELETE FROM workout_exercises WHERE workout_day_id IN (SELECT id FROM workout_days WHERE user_id=?)").bind(uid).run();await db.prepare("DELETE FROM workout_days WHERE user_id=?").bind(uid).run();pos={}
            for x in items:
                await db.prepare("INSERT OR IGNORE INTO workout_days(user_id,weekday,focus) VALUES(?,?,?)").bind(uid,x["weekday"],x["focus"]).run();d=await db.prepare("SELECT id FROM workout_days WHERE user_id=? AND weekday=?").bind(uid,x["weekday"]).first();pos[x["weekday"]]=pos.get(x["weekday"],0)+1;await db.prepare("INSERT INTO workout_exercises(workout_day_id,name,load,sets,reps,position) VALUES(?,?,?,?,?,?)").bind(rowget(d,"id"),x["name"],x.get("load"),x.get("sets"),x.get("reps"),pos[x["weekday"]]).run()
            msg=f"✅ Treino importado: {len(items)} exercício(s). A parte menos atlética da academia foi automatizada."
        await clear_state(db,uid);await send(token,chat,msg,MAIN_KB);return True
    return False

async def handle_message(db,token,message):
    chat=message.get("chat") or {};user=message.get("from") or {};chat_id=chat.get("id")
    if chat_id is None:return
    uid,new,preferred=await ensure_user(db,int(chat_id),user);owner=is_owner(int(chat_id));text=(message.get("text") or "").strip()
    if new and not owner:
        await set_state(db,uid,"ask_name",{});await send(token,int(chat_id),"🕴️ Antes de começar: como você quer que eu te chame?",CANCEL_KB);return
    name=preferred or user.get("first_name") or "chefe"
    if text.startswith("/start") or text=="🏠 Menu principal":await clear_state(db,uid);await menu(token,int(chat_id),name);return
    state,payload=await get_state(db,uid)
    if state and await handle_state(db,token,int(chat_id),uid,owner,state,payload,message):return
    if text in ("Butler, preciso de você","butler, preciso de voce","Chamar, Butler!","chamar, butler!"):
        await db.prepare("UPDATE assistant_state SET day_off=0,updated_at=CURRENT_TIMESTAMP WHERE user_id=?").bind(uid).run();await send(token,int(chat_id),"🕴️ Fala daí, chefe? Voltei. Tente não criar uma emergência administrativa nos primeiros cinco minutos.",MAIN_KB);return
    st=await db.prepare("SELECT day_off FROM assistant_state WHERE user_id=?").bind(uid).first();day_off=int(rowget(st,"day_off",0))
    if text=="🌙 Day-off":await db.prepare("UPDATE assistant_state SET day_off=1,updated_at=CURRENT_TIMESTAMP WHERE user_id=?").bind(uid).run();await send(token,int(chat_id),"🌙 Day-off ativado. Hoje eu finjo que não vi nada. Quando precisar, me chama.",[["Chamar, Butler!"]]);return
    if day_off:await send(token,int(chat_id),"🌙 Estamos de folga, chefe. Se mudou de ideia, manda `Chamar, Butler!`.",[["Chamar, Butler!"]]);return
    if text=="🏠 Cotidiano":await send(token,int(chat_id),"🏠 Cotidiano. A seção onde fingimos que sua vida cabe em botões.",COTIDIANO_KB);return
    if text=="➕ Adicionar":await send(token,int(chat_id),"O que vamos adicionar?",[["✅ Tarefa","📅 Compromisso"],["🏠 Menu principal"]]);return
    if text=="✅ Tarefa":await set_state(db,uid,"task_title",{});await send(token,int(chat_id),"Qual tarefa?",CANCEL_KB);return
    if text=="📅 Compromisso":await set_state(db,uid,"appointment_title",{});await send(token,int(chat_id),"Qual compromisso?",CANCEL_KB);return
    if text=="🗓️ Hoje":await send(token,int(chat_id),await agenda_text(db,uid,now_local().date(),True),AGENDA_KB);return
    if text=="⏭️ Amanhã":await send(token,int(chat_id),await agenda_text(db,uid,now_local().date()+timedelta(days=1),False),AGENDA_KB);return
    if text=="📆 Outra data":await set_state(db,uid,"agenda_date",{});await send(token,int(chat_id),"Qual data? `DD/MM`, `sexta`, `daqui a 3 dias`...",CANCEL_KB);return
    if text=="🗓️ Próximos 7 dias":
        parts=[await agenda_text(db,uid,now_local().date()+timedelta(days=i),False) for i in range(1,8)];await send(token,int(chat_id),"\n\n".join(parts),AGENDA_KB);return
    if text=="📚 Histórico":await send(token,int(chat_id),"Histórico:",[["📖 Histórico diário","🗂️ Histórico de tarefas"],["⬅️ Voltar"]]);return
    if text=="📖 Histórico diário":await set_state(db,uid,"history_date",{});await send(token,int(chat_id),"Qual dia quer revisar?",CANCEL_KB);return
    if text=="🗂️ Histórico de tarefas":await send(token,int(chat_id),await tasks_text(db,uid,"tarefa"),COTIDIANO_KB);return
    if text in ("🛒 Item faltando","🛒 O que está faltando?"):await send(token,int(chat_id),await grocery_text(db,uid),GROCERY_KB);return
    if text in ("➕ Item faltando","➕ Adicionar item"):await set_state(db,uid,"grocery_add",{});await send(token,int(chat_id),"O que está faltando? Pode mandar `sal, açúcar, café`.",CANCEL_KB);return
    if text in ("📋 Ver itens faltando",):await send(token,int(chat_id),await grocery_text(db,uid),GROCERY_KB);return
    if text=="✅ Tarefas":await send(token,int(chat_id),await tasks_text(db,uid,"tarefa"),COTIDIANO_KB);return
    if text=="📅 Compromissos":await send(token,int(chat_id),await tasks_text(db,uid,"compromisso"),COTIDIANO_KB);return
    if text=="👤 Como me chamar":await set_state(db,uid,"rename",{});await send(token,int(chat_id),"Como quer que eu te chame?",CANCEL_KB);return
    if text=="📚 Matérias":await send(token,int(chat_id),"📚 Acadêmico",ACADEMIC_KB);return
    if text=="📚 Minhas matérias":await send(token,int(chat_id),await list_subjects_text(db,uid),ACADEMIC_KB);return
    if text=="⚙️ Gerenciar matérias":await send(token,int(chat_id),"Gerenciar matérias:",MANAGE_SUBJECT_KB);return
    if text=="➕ Adicionar matéria":await set_state(db,uid,"subject_add_name",{});await send(token,int(chat_id),"Nome da matéria?",CANCEL_KB);return
    if text=="🗑️ Remover matéria":await set_state(db,uid,"subject_remove",{});await send(token,int(chat_id),"Nome exato da matéria a remover?",CANCEL_KB);return
    if text=="🚫 Trancar matéria":await set_state(db,uid,"subject_lock",{});await send(token,int(chat_id),"Nome exato da matéria que foi trancada?",CANCEL_KB);return
    if text=="✏️ Editar matéria":await send(token,int(chat_id),"Para evitar editar a matéria errada em produção, por enquanto remova/tranque e adicione novamente com os dados corretos. A edição guiada entra na próxima revisão pequena.",MANAGE_SUBJECT_KB);return
    if text=="📥 Importar grade por PDF/texto":await set_state(db,uid,"import_schedule",{});await send(token,int(chat_id),"📥 Envie PDF com texto pesquisável ou `.txt`. Imagem/scan não entra direto; converta antes.",CANCEL_KB);return
    if text=="🎯 Metas":await send(token,int(chat_id),"🎯 Metas. Sem transformar sua vida num dashboard corporativo.",GOALS_KB);return
    if text=="✅ Registrar progresso":await set_state(db,uid,"goal_progress",{});await send(token,int(chat_id),"Qual? Inglês, Programação, Água, Alimentação ou Musculação.",CANCEL_KB);return
    if text=="🔥 Sequências":await send(token,int(chat_id),await streaks_text(db,uid),GOALS_KB);return
    if text=="🧘 Rotinas":
        rr=await rows(db.prepare("SELECT name,time_hhmm,weekdays FROM routines WHERE user_id=? AND active=1 ORDER BY name").bind(uid));await send(token,int(chat_id),"🧘 Rotinas\n"+("\n".join(f"• {rowget(r,'name')} {rowget(r,'time_hhmm') or ''}" for r in rr) if rr else "Nenhuma rotina cadastrada ainda."),COTIDIANO_KB);return
    if text=="💰 Finanças":await send(token,int(chat_id),"💰 Finanças. Eu registro; você tenta não transformar o relatório em literatura de terror.",FINANCE_KB);return
    if text in ("➕ Entrada","➖ Gasto"):await set_state(db,uid,"finance_amount",{"kind":"entrada" if text=="➕ Entrada" else "saida"});await send(token,int(chat_id),"Quanto? Só o valor, ex.: `35,90`.",CANCEL_KB);return
    if text in ("📊 Resumo do mês","📈 Histórico"):await send(token,int(chat_id),await finance_report(db,uid),FINANCE_KB);return
    if text=="🏋️ Musculação":await send(token,int(chat_id),"🏋️ Academia. Eu acompanho; levantar o peso ainda é uma limitação operacional minha.",WORKOUT_KB);return
    if text=="🚀 Começar os trabalhos":
        if owner:await db.prepare("INSERT INTO protocol_mass_state(user_id,current_week,active,started_at) VALUES(?,1,1,CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET active=1,started_at=COALESCE(started_at,CURRENT_TIMESTAMP)").bind(uid).run()
        await send(token,int(chat_id),"🚀 Começamos os trabalhos. A partir de agora treino entra na conta. Sem pressão. Quer dizer, com uma quantidade administrável de pressão.",WORKOUT_KB);return
    if text=="📅 Treino de hoje":await send(token,int(chat_id),await workout_text(db,uid,owner),WORKOUT_KB);return
    if text=="📝 Registrar série":
        wd,week,active,ex=await workout_plan(db,uid,owner)
        if owner and not active:await send(token,int(chat_id),"Primeiro use 🚀 Começar os trabalhos.",WORKOUT_KB);return
        if not ex:await send(token,int(chat_id),"Não há treino cadastrado hoje.",WORKOUT_KB);return
        await set_state(db,uid,"workout_series_exercise",{});await send(token,int(chat_id),"Qual exercício? Digite o número:\n"+"\n".join(f"{i}. {e['name']}" for i,e in enumerate(ex,1)),CANCEL_KB);return
    if text=="😕 Não consegui treinar hoje":
        if owner:
            s=await db.prepare("SELECT active FROM protocol_mass_state WHERE user_id=?").bind(uid).first()
            if not s or not int(rowget(s,"active",0)):await send(token,int(chat_id),"Ainda não começamos os trabalhos. Não vou registrar falta antes da largada.",WORKOUT_KB);return
        await set_state(db,uid,"workout_skip_reason",{});await send(token,int(chat_id),"Motivo? Pode escrever ou mandar `-`.",CANCEL_KB);return
    if text=="✅ Finalizar treino":
        today=now_local().date();await db.prepare("INSERT INTO workout_logs(user_id,workout_date,weekday,status) VALUES(?,?,?,'feito') ON CONFLICT(user_id,workout_date) DO UPDATE SET status='feito',reason=NULL").bind(uid,today.isoformat(),WEEKDAY_NAMES[today.weekday()]).run()
        if owner:
            s=await db.prepare("SELECT current_week FROM protocol_mass_state WHERE user_id=?").bind(uid).first();week=int(rowget(s,"current_week",1));await db.prepare("INSERT INTO protocol_mass_sessions(user_id,week,weekday,training_date,started_at,completed_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) ON CONFLICT(user_id,week,weekday) DO UPDATE SET completed_at=CURRENT_TIMESTAMP,skipped_at=NULL,skip_reason=NULL").bind(uid,week,WEEKDAY_NAMES[today.weekday()],today.isoformat()).run()
        await send(token,int(chat_id),"✅ Treino concluído. Vou fingir que isso não me deixou discretamente satisfeito.",WORKOUT_KB);return
    if text=="📈 Progresso":
        rr=await rows(db.prepare("SELECT workout_date,status,reason FROM workout_logs WHERE user_id=? ORDER BY workout_date DESC LIMIT 14").bind(uid));await send(token,int(chat_id),"📈 Academia\n"+("\n".join(f"{'✅' if rowget(r,'status')=='feito' else '➖'} {rowget(r,'workout_date')}"+(f" — {rowget(r,'reason')}" if rowget(r,'reason') else "") for r in rr) if rr else "Ainda sem registros."),WORKOUT_KB);return
    if text=="🔄 Reiniciar treinos":
        await db.prepare("DELETE FROM workout_logs WHERE user_id=?").bind(uid).run();await db.prepare("DELETE FROM workout_set_logs WHERE user_id=?").bind(uid).run();await db.prepare("DELETE FROM protocol_mass_sessions WHERE user_id=?").bind(uid).run();await db.prepare("DELETE FROM protocol_mass_set_logs WHERE user_id=?").bind(uid).run();await db.prepare("UPDATE protocol_mass_state SET current_week=1,active=0,started_at=NULL,finished_at=NULL WHERE user_id=?").bind(uid).run();await send(token,int(chat_id),"🔄 Progresso zerado. O plano continua salvo; quando quiser recomeçar, use 🚀 Começar os trabalhos.",WORKOUT_KB);return
    if text=="📥 Importar treino por PDF/texto":await set_state(db,uid,"import_workout",{});await send(token,int(chat_id),"📥 Envie PDF textual ou `.txt`. Ex.: `SEGUNDA — Peito` / `Supino reto | 4x8-10 | 40 kg`.",CANCEL_KB);return
    if text=="🔁 Substituir exercício":await send(token,int(chat_id),"🔁 No treino pessoal eu uso a tabela de substituições quando reconheço o exercício; no genérico, ainda não invento substituto sem referência. Pode registrar a série pelo nome do exercício substituto e eu mantenho o histórico.",WORKOUT_KB);return
    if await handle_natural(db,token,int(chat_id),uid,owner,text):return
    await send(token,int(chat_id),"🕴️ Não peguei essa. Tenta falar de tarefa, compromisso, mercado, agenda, treino ou finanças — ou usa os botões. Ainda estou aprendendo a ser útil sem virar vidente.",MAIN_KB)

async def morning_summary(db,uid,chat,token,today):
    text=await agenda_text(db,uid,today,True);g=await rows(db.prepare("SELECT name FROM grocery_items WHERE user_id=? AND missing=1 ORDER BY name LIMIT 5").bind(uid));extra=""
    if g:extra="\n\n🛒 Faltando em casa: "+", ".join(rowget(r,"name") for r in g)
    yesterday=today-timedelta(days=1);pend=await rows(db.prepare("SELECT title FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente' AND due_date=?").bind(uid,yesterday.isoformat()))
    if pend:extra+="\n\n📎 Ontem deixou herança:\n"+"\n".join(f"• {rowget(r,'title')}" for r in pend)+"\nElas sobreviveram à virada do dia. Impressionante persistência."
    await send(token,chat,"☀️ Resumo da manhã\n\n"+text+extra+"\n\nNada demais. Só a administração básica de uma pequena empresa chamada sua vida. 😌",MAIN_KB)

async def weekly_summary(db,uid,chat,token,today):
    start=today-timedelta(days=6);done=await db.prepare("SELECT COUNT(*) n FROM daily_items WHERE user_id=? AND status='concluido' AND date(completed_at)>=?").bind(uid,start.isoformat()).first();pending=await db.prepare("SELECT COUNT(*) n FROM daily_items WHERE user_id=? AND status='pendente' AND due_date<=?").bind(uid,today.isoformat()).first();work=await db.prepare("SELECT COUNT(*) n FROM workout_logs WHERE user_id=? AND status='feito' AND workout_date>=?").bind(uid,start.isoformat()).first();await send(token,chat,f"📊 Fechamento semanal\n\n✅ Tarefas concluídas: {rowget(done,'n',0)}\n📌 Pendências abertas: {rowget(pending,'n',0)}\n🏋️ Treinos feitos: {rowget(work,'n',0)}\n\nBoa ou torta, a semana acabou. Segunda a gente finge surpresa e começa de novo. 😏",MAIN_KB)

async def scheduled_tick(db,token):
    now=now_local();today=now.date();weekday=WEEKDAY_NAMES[today.weekday()]
    users=await rows(db.prepare("SELECT u.id,u.telegram_chat_id,a.day_off FROM users u JOIN assistant_state a ON a.user_id=u.id"))
    for u in users:
        uid=int(rowget(u,"id"));chat=int(rowget(u,"telegram_chat_id"));
        if int(rowget(u,"day_off",0)):continue
        if now.hour==MORNING_SUMMARY_HOUR and now.minute==MORNING_SUMMARY_MINUTE:
            key=f"morning:{today.isoformat()}";e=await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid,key).first()
            if not e:await morning_summary(db,uid,chat,token,today);await db.prepare("INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid,key).run()
        if today.weekday()==WEEKLY_SUMMARY_WEEKDAY and now.hour==WEEKLY_SUMMARY_HOUR and now.minute==WEEKLY_SUMMARY_MINUTE:
            key=f"weekly:{today.isoformat()}";e=await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid,key).first()
            if not e:await weekly_summary(db,uid,chat,token,today);await db.prepare("INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid,key).run()
        # Aulas: aviso 10 minutos antes.
        sessions=await rows(db.prepare("SELECT s.name,ss.start_time,ss.location FROM subjects s JOIN subject_sessions ss ON ss.subject_id=s.id WHERE s.user_id=? AND s.active=1 AND ss.weekday=?").bind(uid,weekday))
        for r in sessions:
            h,m=map(int,rowget(r,"start_time").split(":"));target=datetime.combine(today,datetime.min.time()).replace(hour=h,minute=m)-timedelta(minutes=10)
            if now.hour==target.hour and now.minute==target.minute:
                key=f"class:{today}:{rowget(r,'name')}:{rowget(r,'start_time')}";e=await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid,key).first()
                if not e:await send(token,chat,f"🎓 Chefe, {rowget(r,'name')} começa às {rowget(r,'start_time')} ({rowget(r,'location') or 'local não informado'}). Dez minutos. Hora de existir academicamente.",MAIN_KB);await db.prepare("INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid,key).run()
        items=await rows(db.prepare("SELECT id,kind,title,due_time FROM daily_items WHERE user_id=? AND status='pendente' AND due_date=? AND due_time IS NOT NULL").bind(uid,today.isoformat()))
        for r in items:
            h,m=map(int,rowget(r,"due_time").split(":"));advance=10 if rowget(r,"kind")=="compromisso" else 0;target=datetime.combine(today,datetime.min.time()).replace(hour=h,minute=m)-timedelta(minutes=advance)
            if now.hour==target.hour and now.minute==target.minute:
                key=f"item:{rowget(r,'id')}:{today}:{target.strftime('%H:%M')}";e=await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid,key).first()
                if not e:await send(token,chat,("📅" if rowget(r,"kind")=="compromisso" else "✅")+f" {rowget(r,'title')} — {rowget(r,'due_time')}. {'Dez minutos. Se organize.' if advance else 'Está na hora. Eu fiz minha parte.'}",MAIN_KB);await db.prepare("INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid,key).run()
