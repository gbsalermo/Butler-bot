import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

import app
import conversation_layer
import routine_integration
import runtime_guard
from owner_profile import is_owner
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
DAY_NAMES = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
DAY_ALIASES = {
    "segunda": 0, "segunda feira": 0, "seg": 0,
    "terca": 1, "terca feira": 1, "ter": 1,
    "quarta": 2, "quarta feira": 2, "qua": 2,
    "quinta": 3, "quinta feira": 3, "qui": 3,
    "sexta": 4, "sexta feira": 4, "sex": 4,
    "sabado": 5, "sab": 5,
    "domingo": 6, "dom": 6,
}
ACADEMIC_KB = [
    ["📚 Minhas matérias", "⚙️ Gerenciar matérias"],
    ["📝 Adicionar prova", "📋 Provas"],
    ["📥 Importar grade por PDF/texto"],
    ["🏠 Menu principal"],
]
ROUTINE_KB = [
    ["➕ Adicionar rotina", "📋 Minhas rotinas"],
    ["✅ Marcar rotina feita", "🏁 Encerrar rotina hoje"],
    ["🗑️ Remover rotina"],
    ["⬅️ Voltar ao cotidiano"],
]
CANCEL_KB = [["❌ Cancelar ação"]]


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9:/ ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


async def _rows(stmt):
    result = await stmt.all()
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(_row(row, "id")) if row else None


def _next_weekday(target_weekday, today, strict=False):
    delta = (target_weekday - today.weekday()) % 7
    if strict and delta == 0:
        delta = 7
    return today + timedelta(days=delta)


def _weekday_from_text(text):
    n = _norm(text)
    for label, idx in sorted(DAY_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{re.escape(label)}\b", n):
            return idx
    return None


def _day_of_month(text, today):
    n = _norm(text)
    m = re.search(r"\bdia\s+(\d{1,2})\b", n)
    if not m:
        return None
    d = int(m.group(1))
    year, month = today.year, today.month
    for _ in range(14):
        try:
            candidate = date(year, month, d)
            if candidate >= today:
                return candidate
        except ValueError:
            pass
        month += 1
        if month == 13:
            month = 1
            year += 1
    return None


def _date_from_phrase(text, today):
    n = _norm(text)
    if "depois de amanha" in n:
        return today + timedelta(days=2)
    if re.search(r"\bamanha\b", n):
        return today + timedelta(days=1)
    if re.search(r"\bhoje\b", n):
        return today
    dom = _day_of_month(text, today)
    if dom:
        return dom
    wd = _weekday_from_text(text)
    if wd is not None:
        strict = any(x in n for x in ("proxima", "proximo", "que vem"))
        return _next_weekday(wd, today, strict=strict)
    return app.parse_date(text, today)


def _next_week_bounds(today):
    this_monday = today - timedelta(days=today.weekday())
    start = this_monday + timedelta(days=7)
    return start, start + timedelta(days=6)


def _weekend_bounds(today):
    saturday = _next_weekday(5, today, strict=False)
    return saturday, saturday + timedelta(days=1)


def _time_window(text):
    n = _norm(text)
    if "de manha" in n or "pela manha" in n:
        return "05:00", "11:59", "de manhã"
    if "a tarde" in n or "de tarde" in n or "pela tarde" in n:
        return "12:00", "17:59", "à tarde"
    if "a noite" in n or "de noite" in n or "pela noite" in n:
        return "18:00", "23:59", "à noite"
    return None


def _snark_empty(topic="agenda"):
    if topic == "compromisso":
        return "Nada. Seu calendário decidiu colaborar pela primeira vez sem reunião para provar que colaborou. 😌"
    if topic == "aula":
        return "Não achei próxima aula disso. Ou você está livre, ou finalmente descobrimos um buraco na grade."
    return "Nada marcado. Um raro momento em que o calendário não está tentando administrar você. Aproveite com responsabilidade duvidosa. 😏"


async def _agenda_range(db, uid, start, end, title):
    parts = [f"📆 {title}"]
    cur = start
    found = False
    while cur <= end:
        text = await app.agenda_text(db, uid, cur, False)
        # Só inclui dias que tenham conteúdo real.
        if "Nada marcado" not in text:
            parts.append(text)
            found = True
        cur += timedelta(days=1)
    if not found:
        parts.append(_snark_empty())
    return "\n\n".join(parts)


async def _specific_commitments(db, uid, target, window=None):
    sql = "SELECT id,title,due_time FROM daily_items WHERE user_id=? AND kind='compromisso' AND status='pendente' AND due_date=? AND COALESCE(details,'') NOT LIKE 'exam:%'"
    params = [uid, target.isoformat()]
    if window:
        sql += " AND due_time BETWEEN ? AND ?"
        params.extend([window[0], window[1]])
    sql += " ORDER BY due_time,id"
    return await _rows(db.prepare(sql).bind(*params))


async def _next_commitment(db, uid):
    now = _now(); today = now.date().isoformat(); current = now.strftime("%H:%M")
    return await db.prepare("""
        SELECT id,title,due_date,due_time FROM daily_items
        WHERE user_id=? AND kind='compromisso' AND status='pendente'
          AND COALESCE(details,'') NOT LIKE 'exam:%'
          AND due_date IS NOT NULL
          AND (due_date>? OR (due_date=? AND (due_time IS NULL OR due_time>=?)))
        ORDER BY due_date,COALESCE(due_time,'99:99'),id LIMIT 1
    """).bind(uid,today,today,current).first()


async def _next_class(db, uid, subject_query):
    q = _norm(subject_query)
    subjects = await _rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND active=1").bind(uid))
    matches = [s for s in subjects if q in _norm(_row(s,"name")) or _norm(_row(s,"name")) in q]
    if len(matches) != 1:
        return None, matches
    subject = matches[0]
    sessions = await _rows(db.prepare("SELECT weekday,start_time,end_time,location FROM subject_sessions WHERE subject_id=? ORDER BY start_time").bind(_row(subject,"id")))
    now = _now(); best = None
    for session in sessions:
        wd_text = _norm(_row(session,"weekday"))
        wd = None
        for label, idx in DAY_ALIASES.items():
            if label in wd_text:
                wd = idx; break
        if wd is None:
            continue
        d = _next_weekday(wd, now.date(), strict=False)
        h,m = map(int,_row(session,"start_time").split(":"))
        dt = datetime.combine(d, datetime.min.time()).replace(hour=h,minute=m,tzinfo=LOCAL_TZ)
        if dt < now:
            dt += timedelta(days=7)
        if best is None or dt < best[0]:
            best = (dt, session, subject)
    return best, matches


async def _academia_week(db, uid, chat_id):
    today = _now().date(); monday = today - timedelta(days=today.weekday())
    owner = is_owner(int(chat_id))
    items=[]
    for i in range(7):
        d=monday+timedelta(days=i)
        try:
            weekday, week, active, exercises = await app.workout_plan(db, uid, owner, d)
        except Exception:
            exercises=[]; active=True; week=None
        if exercises and (not owner or active):
            focus_row = await db.prepare("SELECT focus FROM workout_days WHERE user_id=? AND weekday=?").bind(uid, app.WEEKDAY_NAMES[d.weekday()]).first()
            focus = _row(focus_row,"focus") or f"{len(exercises)} exercício(s)"
            items.append((d,focus,week))
    if not items:
        # fallback para ficha genérica cadastrada.
        days = await _rows(db.prepare("SELECT weekday,focus FROM workout_days WHERE user_id=? ORDER BY id").bind(uid))
        return days
    return items


async def _subject_lookup(db, uid, text):
    subjects = await _rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    n=_norm(text)
    exact=[s for s in subjects if _norm(_row(s,"name"))==n]
    if exact: return exact[0],subjects
    partial=[s for s in subjects if n in _norm(_row(s,"name")) or _norm(_row(s,"name")) in n]
    return (partial[0] if len(partial)==1 else None),subjects


async def _exam_list(db,uid):
    today=_now().date().isoformat()
    rs=await _rows(db.prepare("""
      SELECT di.id,di.title,di.due_date,di.due_time,s.name subject
      FROM daily_items di LEFT JOIN subjects s
        ON di.details='exam:'||s.id
      WHERE di.user_id=? AND di.kind='compromisso' AND di.status='pendente'
        AND di.details LIKE 'exam:%' AND di.due_date>=?
      ORDER BY di.due_date,COALESCE(di.due_time,'99:99')
    """).bind(uid,today))
    if not rs:
        return "📝 Nenhuma prova futura cadastrada. Estranhamente pacífico. Não se acostume."
    out=["📝 Próximas provas"]
    for r in rs:
        when=f"{_row(r,'due_date')[8:10]}/{_row(r,'due_date')[5:7]}"+(f" às {_row(r,'due_time')}" if _row(r,'due_time') else "")
        out.append(f"• #{_row(r,'id')} {_row(r,'subject') or _row(r,'title')} — {when}")
    out.append("\nEu aviso antes. Porque descobrir prova na manhã da prova é um método de estudo, mas não um bom. 😌")
    return "\n".join(out)


async def _save_exam(db,uid,subject,due_date,due_time=None):
    title=f"Prova de {_row(subject,'name')}"
    await db.prepare("INSERT INTO daily_items(user_id,kind,title,details,due_date,due_time,status) VALUES(?,'compromisso',?,?,?,?,'pendente')").bind(uid,title,f"exam:{_row(subject,'id')}",due_date.isoformat(),due_time).run()
    return title


async def _complete_routine_all(db,uid,routine):
    scheduled=routine_integration._times(_row(routine,"time_hhmm"))
    today=_now().date()
    done=set(scheduled) if scheduled else {"feito"}
    await db.prepare("INSERT INTO routine_logs(routine_id,log_date,status) VALUES(?,?,'feito') ON CONFLICT(routine_id,log_date) DO UPDATE SET status='feito'").bind(_row(routine,"id"),today.isoformat()).run()
    category=_row(routine,"category")
    goal=await db.prepare("SELECT id FROM goals WHERE user_id=? AND lower(name)=lower(?) LIMIT 1").bind(uid,category).first()
    if goal:
        note=f"rotina:{_row(routine,'id')}"
        gid=int(_row(goal,"id"))
        await db.prepare("INSERT INTO goal_progress(goal_id,amount,log_date,note) SELECT ?,1,?,? WHERE NOT EXISTS(SELECT 1 FROM goal_progress WHERE goal_id=? AND log_date=? AND note=?)").bind(gid,today.isoformat(),note,gid,today.isoformat(),note).run()
    return len(done), max(len(scheduled),1)


async def _find_routine(db,uid,text):
    rs=await _rows(db.prepare("SELECT id,name,category,time_hhmm,weekdays FROM routines WHERE user_id=? AND active=1").bind(uid))
    n=_norm(text)
    stop={"ja","bebi","a","meta","de","do","da","toda","todo","tudo","estudei","fiz","cumpri","completei","terminei","rotina","hoje","minha","meu","ingles","agua"}
    # Primeiro tenta nome/categoria completos.
    matches=[]
    for r in rs:
        hay=_norm((_row(r,"name") or "")+" "+(_row(r,"category") or ""))
        if any(x in n for x in (_norm(_row(r,"name") or ""),_norm(_row(r,"category") or "")) if len(x)>=3):
            matches.append(r)
    if len(matches)==1:return matches[0],rs
    # Depois token relevante, útil para "já estudei inglês" / "meta de água".
    tokens=[t for t in n.split() if len(t)>=3 and t not in stop]
    matches=[r for r in rs if any(t in _norm((_row(r,"name") or "")+" "+(_row(r,"category") or "")) for t in tokens)]
    return (matches[0] if len(matches)==1 else None),rs


async def handle_message(db,token,message):
    chat=(message.get("chat") or {}).get("id")
    if chat is None:return False
    uid=await _uid(db,int(chat))
    if not uid:return False
    text=(message.get("text") or "").strip(); n=_norm(text); today=_now().date()

    # Estado de cadastro de prova / encerramento de rotina.
    state,payload=await runtime_guard._state(db,uid)
    if state=="ai_exam_subject":
        subject,subjects=await _subject_lookup(db,uid,text)
        if not subject:
            await send_message(token,int(chat),"Não achei uma matéria única com esse nome. Escolha uma da lista — prometo não inventar uma disciplina eletiva no susto.",reply_markup=_kb(CANCEL_KB));return True
        await runtime_guard._set_state(db,uid,"ai_exam_date",{"subject_id":int(_row(subject,"id")),"subject":_row(subject,"name")})
        await send_message(token,int(chat),f"Quando é a prova de {_row(subject,'name')}? Ex.: `25/08`, `dia 25` ou `próxima terça`.",reply_markup=_kb(CANCEL_KB));return True
    if state=="ai_exam_date":
        d=_date_from_phrase(text,today)
        if not d or d<today:
            await send_message(token,int(chat),"Não reconheci uma data futura. A prova pode ser cruel; viagem no tempo ainda não entrou no currículo.",reply_markup=_kb(CANCEL_KB));return True
        payload["date"]=d.isoformat();await runtime_guard._set_state(db,uid,"ai_exam_time",payload)
        await send_message(token,int(chat),"Horário da prova? Ex.: `14h`, `14:30` ou `sem horário`.",reply_markup=_kb(CANCEL_KB));return True
    if state=="ai_exam_time":
        tm=None if n in ("sem horario","nao sei","sem hora") else app.parse_time(text)
        if tm is None and n not in ("sem horario","nao sei","sem hora"):
            await send_message(token,int(chat),"Manda `14h`, `14:30` ou `sem horário`. Não vou sortear o horário da prova; já basta a matéria sortear questão. 😏",reply_markup=_kb(CANCEL_KB));return True
        subject=await db.prepare("SELECT id,name FROM subjects WHERE id=? AND user_id=?").bind(payload["subject_id"],uid).first()
        d=date.fromisoformat(payload["date"]);title=await _save_exam(db,uid,subject,d,tm)
        await runtime_guard._clear(db,uid)
        await send_message(token,int(chat),f"📝 {title} cadastrada para {d.strftime('%d/%m')}"+(f" às {tm}" if tm else "")+". Vou começar a te incomodar antes, porque pânico de última hora já tem voluntários suficientes.",reply_markup=_kb(ACADEMIC_KB));return True
    if state=="ai_finish_routine":
        routine,_=await _find_routine(db,uid,text)
        if not routine:
            await send_message(token,int(chat),"Qual rotina você encerrou hoje? Manda o nome como aparece em Minhas rotinas.",reply_markup=_kb(CANCEL_KB));return True
        done,total=await _complete_routine_all(db,uid,routine);await runtime_guard._clear(db,uid)
        await send_message(token,int(chat),f"🏁 {_row(routine,'name')} encerrada hoje: {done}/{total}. Marquei todos os checkpoints e dei o crédito da meta. Sim, desta vez vou acreditar em você sem abrir sindicância. 😌",reply_markup=_kb(ROUTINE_KB));return True

    # Botões acadêmicos / rotina inteira.
    if text=="📝 Adicionar prova":
        subjects=await _rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
        if not subjects:
            await send_message(token,int(chat),"Você precisa cadastrar a matéria antes da prova. Até o caos acadêmico precisa de chave estrangeira. 😌",reply_markup=_kb(ACADEMIC_KB));return True
        await runtime_guard._set_state(db,uid,"ai_exam_subject",{})
        await send_message(token,int(chat),"De qual matéria é a prova?\n\n"+"\n".join(f"• {_row(s,'name')}" for s in subjects),reply_markup=_kb(CANCEL_KB));return True
    if text=="📋 Provas":
        await send_message(token,int(chat),await _exam_list(db,uid),reply_markup=_kb(ACADEMIC_KB));return True
    if text=="🏁 Encerrar rotina hoje":
        rs=await _rows(db.prepare("SELECT id,name FROM routines WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
        if not rs:
            await send_message(token,int(chat),"Não há rotina ativa para encerrar. Excelente eficiência: eliminamos até a obrigação. 😌",reply_markup=_kb(ROUTINE_KB));return True
        await runtime_guard._set_state(db,uid,"ai_finish_routine",{})
        await send_message(token,int(chat),"Qual rotina foi completamente cumprida hoje?\n\n"+"\n".join(f"• {_row(r,'name')}" for r in rs),reply_markup=_kb(CANCEL_KB));return True

    # Encerrar rotina inteira por frase. "bebi água" continua checkpoint; meta/tudo ou atividades como estudei encerram o dia.
    full_routine = (
        ("bebi" in n and any(x in n for x in ("meta", "tudo", "toda", "2 litros", "dois litros")))
        or re.search(r"\b(?:ja\s+)?(?:estudei|treinei|meditei|li|pratiquei)\b",n)
        or any(x in n for x in ("cumpri a rotina", "completei a rotina", "terminei a rotina", "fiz a rotina toda", "encerra a rotina"))
    )
    if full_routine:
        routine,_=await _find_routine(db,uid,text)
        if routine:
            done,total=await _complete_routine_all(db,uid,routine)
            await send_message(token,int(chat),f"🏁 {_row(routine,'name')} fechada por hoje: {done}/{total}. Meta contabilizada. Agora pode seguir fingindo que disciplina foi uma decisão espontânea. 😏",reply_markup=_kb(ROUTINE_KB));return True

    # Cadastro natural de prova.
    if "prova" in n and any(x in n for x in ("tenho prova", "marca prova", "adiciona prova", "cadastra prova", "prova de")):
        d=_date_from_phrase(text,today);tm=app.parse_time(text)
        m=re.search(r"prova\s+(?:de|da|do)\s+(.+?)(?=\s+(?:hoje|amanha|dia\s+\d|segunda|terca|quarta|quinta|sexta|sabado|domingo|as\s+\d)|$)",n)
        subject_text=m.group(1).strip() if m else ""
        subject,_=await _subject_lookup(db,uid,subject_text)
        if subject and d:
            title=await _save_exam(db,uid,subject,d,tm)
            await send_message(token,int(chat),f"📝 {title}: {d.strftime('%d/%m')}"+(f" às {tm}" if tm else "")+". Registrado. Agora a estratégia revolucionária é lembrar disso antes da véspera. Eu cuido da parte dos avisos. 😌",reply_markup=_kb(ACADEMIC_KB));return True

    # 9. Próxima aula de matéria.
    if "proxima aula" in n or (n.startswith("quando") and "aula" in n):
        m=re.search(r"aula\s+(?:de|da|do)\s+(.+)$",n)
        query=m.group(1).strip() if m else re.sub(r"^.*?aula\s+","",n).strip()
        best,matches=await _next_class(db,uid,query)
        if best:
            dt,session,subject=best
            await send_message(token,int(chat),f"🎓 Próxima aula de {_row(subject,'name')}: {DAY_NAMES[dt.weekday()].capitalize()}, {dt.strftime('%d/%m')} às {dt.strftime('%H:%M')}"+(f" — {_row(session,'location')}" if _row(session,'location') else "")+". Sim, eu consultei a grade para você não precisar abrir o portal como se fosse 2014. 😌",reply_markup=_kb(app.AGENDA_KB));return True
        if matches:
            await send_message(token,int(chat),"Achei mais de uma matéria parecida. Seja um pouco mais específico; nem o Butler corrige ambiguidade por osmose.",reply_markup=_kb(ACADEMIC_KB));return True

    # 10. Academia essa semana.
    if "academia" in n and "semana" in n and any(x in n for x in ("quando", "quais dias", "que dia", "tenho")):
        info=await _academia_week(db,uid,int(chat))
        if info and isinstance(info[0],tuple):
            lines=["🏋️ Academia nesta semana:"]
            for d,focus,week in info:
                lines.append(f"• {DAY_NAMES[d.weekday()].capitalize()} {d.strftime('%d/%m')} — {focus}"+(f" (semana {week}/12)" if week else ""))
            lines.append("\nO calendário mostrou os dias. O halter, infelizmente, ainda exige presença física. 😏")
        elif info:
            lines=["🏋️ Sua ficha tem:"]+[f"• {_row(r,'weekday').capitalize()} — {_row(r,'focus')}" for r in info]
        else:
            lines=["🏋️ Não achei treino cadastrado para esta semana. O sofá apresentou documentação convincente, pelo visto."]
        await send_message(token,int(chat),"\n".join(lines),reply_markup=_kb(app.WORKOUT_KB));return True

    # 11. Próximo compromisso.
    if any(x in n for x in ("qual meu proximo compromisso", "qual o proximo compromisso", "quando e meu proximo compromisso", "proximo compromisso")):
        r=await _next_commitment(db,uid)
        if not r:
            msg=_snark_empty("compromisso")
        else:
            msg=f"📅 Seu próximo compromisso é {_row(r,'title')} — {_row(r,'due_date')[8:10]}/{_row(r,'due_date')[5:7]}"+(f" às {_row(r,'due_time')}" if _row(r,'due_time') else "")+". Anotado. Agora só falta a parte ousada de chegar no horário. 😏"
        await send_message(token,int(chat),msg,reply_markup=_kb(app.AGENDA_KB));return True

    # 8. Compromisso amanhã à tarde / manhã / noite.
    if "compromisso" in n and any(x in n for x in ("tenho algum", "tenho compromisso", "quais compromissos")):
        d=_date_from_phrase(text,today)
        window=_time_window(text)
        if d and window:
            rs=await _specific_commitments(db,uid,d,window)
            if rs:
                msg=f"📅 Compromissos {window[2]} em {d.strftime('%d/%m')}:\n"+"\n".join(f"• {_row(r,'due_time') or '--:--'} — {_row(r,'title')}" for r in rs)+"\n\nSim, existe vida depois do almoço. O calendário confirmou. 😌"
            else:msg=f"📅 Nenhum compromisso {window[2]} em {d.strftime('%d/%m')}. {_snark_empty('compromisso')}"
            await send_message(token,int(chat),msg,reply_markup=_kb(app.AGENDA_KB));return True

    # 6. Fim de semana.
    if "fim de semana" in n and any(x in n for x in ("o que tenho", "agenda", "como ta", "como esta", "tenho")):
        start,end=_weekend_bounds(today)
        await send_message(token,int(chat),await _agenda_range(db,uid,start,end,f"Fim de semana — {start.strftime('%d/%m')} a {end.strftime('%d/%m')}"),reply_markup=_kb(app.AGENDA_KB));return True

    # 7. Semana que vem.
    if "semana que vem" in n or "proxima semana" in n:
        start,end=_next_week_bounds(today)
        await send_message(token,int(chat),await _agenda_range(db,uid,start,end,f"Próxima semana — {start.strftime('%d/%m')} a {end.strftime('%d/%m')}"),reply_markup=_kb(app.AGENDA_KB));return True

    # 1-5. Agenda em dia específico: próxima terça, terça, terça que vem, dia 25, como tá quarta.
    agenda_signal = any(x in n for x in ("agenda", "o que tenho", "tenho algo", "como ta minha", "como esta minha", "como ta a minha", "como esta a minha"))
    if agenda_signal:
        d=_date_from_phrase(text,today)
        if d:
            await send_message(token,int(chat),await app.agenda_text(db,uid,d,True),reply_markup=_kb(app.AGENDA_KB));return True

    return False


async def exam_reminders(db,token):
    now=_now();today=now.date();current=now.strftime("%H:%M")
    users=await _rows(db.prepare("SELECT u.id,u.telegram_chat_id,a.day_off FROM users u JOIN assistant_state a ON a.user_id=u.id"))
    for user in users:
        if int(_row(user,"day_off",0)):continue
        uid=int(_row(user,"id"));chat=int(_row(user,"telegram_chat_id"))
        exams=await _rows(db.prepare("SELECT id,title,due_date,due_time FROM daily_items WHERE user_id=? AND status='pendente' AND details LIKE 'exam:%' AND due_date>=?").bind(uid,today.isoformat()))
        for exam in exams:
            d=date.fromisoformat(_row(exam,"due_date"));days=(d-today).days;iid=int(_row(exam,"id"))
            moments=[]
            if days in (7,3,1) and current=="09:00":moments.append((f"d{days}",f"📝 {_row(exam,'title')} em {days} dia{'s' if days!=1 else ''}."))
            if days==0 and current=="07:30":moments.append(("today",f"📝 É hoje: {_row(exam,'title')}"+(f" às {_row(exam,'due_time')}" if _row(exam,'due_time') else "")+". Agora fingir surpresa exigiria atuação demais até para você. 😌"))
            if days==0 and _row(exam,"due_time"):
                h,m=map(int,_row(exam,"due_time").split(":"));one_hour=(datetime.combine(d,datetime.min.time()).replace(hour=h,minute=m)-timedelta(hours=1)).strftime("%H:%M")
                if current==one_hour:moments.append(("h1",f"⏰ {_row(exam,'title')} em 1 hora. Revisão final, água e dignidade. Nessa ordem se possível. 😏"))
            for code,msg in moments:
                key=f"exam:{iid}:{d.isoformat()}:{code}"
                exists=await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid,key).first()
                if exists:continue
                await send_message(token,chat,msg,reply_markup=_kb(ACADEMIC_KB))
                await db.prepare("INSERT INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid,key).run()


def install():
    app.ACADEMIC_KB = ACADEMIC_KB
    runtime_guard.ROUTINE_KB = ROUTINE_KB
    routine_integration.ROUTINE_KB = ROUTINE_KB
    original_scheduler=app.scheduled_tick
    async def scheduler(db,token):
        await original_scheduler(db,token)
        await exam_reminders(db,token)
    app.scheduled_tick=scheduler
