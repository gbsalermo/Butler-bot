"""Progressão de carga e cardio diário para a musculação.

- adiciona Cardio (30 min) ao treino diário;
- mostra última referência e maior carga registrada no treino de hoje;
- permite consultar histórico de cargas por semana/dia;
- reutiliza protocol_mass_set_logs/workout_set_logs: não cria segunda fonte de verdade.
"""
import re

import app
from telegram_api import send_message

_ORIGINAL_PLAN = app.workout_plan
_ORIGINAL_TEXT = app.workout_text

HISTORY_BUTTON = "📊 Histórico de cargas"


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


def _num_load(value):
    if value is None:return None
    m=re.search(r"-?\d+(?:[.,]\d+)?",str(value))
    if not m:return None
    try:return float(m.group(0).replace(",","."))
    except Exception:return None


def _fmt_ref(row):
    if not row:return None
    load=str(_row(row,"load") or "-"); reps=str(_row(row,"reps") or "-")
    week=_row(row,"week"); day=_row(row,"weekday")
    where=""
    if week:where+=f" • sem. {week}"
    if day:where+=f" • {str(day).replace('-feira','')}"
    return f"{load} × {reps}{where}"

async def _history_rows(db,uid,exercise=None,limit=200):
    if exercise:
        return await _rows(db.prepare("""SELECT week,weekday,exercise_name,set_number,load,reps,id
            FROM protocol_mass_set_logs WHERE user_id=? AND lower(exercise_name)=lower(?)
            ORDER BY id DESC LIMIT ?""").bind(uid,exercise,limit))
    return await _rows(db.prepare("""SELECT week,weekday,exercise_name,set_number,load,reps,id
        FROM protocol_mass_set_logs WHERE user_id=? ORDER BY id DESC LIMIT ?""").bind(uid,limit))

async def _references(db,uid,exercise,current_week=None):
    rows=await _history_rows(db,uid,exercise,100)
    if current_week is not None:
        previous=[r for r in rows if int(_row(r,"week",0) or 0)<int(current_week)]
        if previous:rows=previous
    if not rows:return None,None
    last=rows[0]
    numeric=[(_num_load(_row(r,"load")),r) for r in rows]
    numeric=[x for x in numeric if x[0] is not None]
    best=max(numeric,key=lambda x:x[0])[1] if numeric else last
    return last,best

async def workout_plan_with_cardio(db,uid,owner,target=None):
    wd,week,active,ex=await _ORIGINAL_PLAN(db,uid,owner,target)
    # Cardio é parte fixa do dia, inclusive quando o protocolo não tiver musculação
    # cadastrada naquele dia. O registro usa a mesma tabela de séries.
    cardio={"name":"Cardio","sets":1,"load":None,"reps":"30 min","raw":{"name":"Cardio","series":1,"reps":"30 min","extra":True}}
    if not any(str(e.get("name") or "").lower()=="cardio" for e in ex):
        ex=list(ex)+[cardio]
    return wd,week,active,ex

async def workout_text_with_references(db,uid,owner):
    wd,week,active,ex=await workout_plan_with_cardio(db,uid,owner)
    if owner and not active:
        return "🏋️ Os trabalhos ainda não começaram. Use 🚀 Começar os trabalhos quando quiser iniciar as 12 semanas."
    if not ex:return f"🏋️ Não há treino cadastrado para {wd}."
    out=[f"🏋️ Treino de {wd.capitalize()}"+(f" — semana {week}/12" if week else "")]
    for i,e in enumerate(ex,1):
        name=e.get("name"); raw=e.get("raw") or {}; scheme=e.get("sets") or raw.get("series") or ""
        planned=[]
        reps=e.get("reps") or raw.get("reps") or raw.get("repeticoes") or raw.get("repetições")
        load=e.get("load") or raw.get("carga") or raw.get("load")
        if reps:planned.append(str(reps))
        if load:planned.append(str(load))
        line=f"{i}. {name} — {scheme}"+(" • "+" • ".join(planned) if planned else "")
        if str(name).lower()=="cardio":
            line=f"{i}. 🫀 Cardio — 30 min"
        last,best=await _references(db,uid,name,week if owner else None)
        if last:
            line+=f"\n   ↳ Última referência: {_fmt_ref(last)}"
            if best and _row(best,"id")!=_row(last,"id"):
                line+=f"\n   ↳ Maior carga anterior: {_fmt_ref(best)}"
        else:
            line+="\n   ↳ Sem referência anterior"
        out.append(line)
    return "\n".join(out)

async def _history_text(db,uid):
    rows=await _history_rows(db,uid,None,250)
    if not rows:return "📊 Ainda não há séries registradas no protocolo. Quando você alimentar carga/repetições, eu monto o histórico daqui."
    groups={}
    for r in reversed(rows):
        key=(int(_row(r,"week",0) or 0),str(_row(r,"weekday") or ""))
        groups.setdefault(key,[]).append(r)
    out=["📊 Histórico de cargas — Protocol Mass"]
    for (week,day),items in sorted(groups.items(),key=lambda x:(x[0][0],x[0][1])):
        out.append(f"\n🗓️ Semana {week} • {day.replace('-feira','').capitalize()}")
        by_ex={}
        for r in items:by_ex.setdefault(str(_row(r,"exercise_name")),[]).append(r)
        for name,sets in by_ex.items():
            values=" | ".join(f"S{_row(r,'set_number')}: {_row(r,'load') or '-'} × {_row(r,'reps') or '-'}" for r in sets)
            numeric=[(_num_load(_row(r,"load")),r) for r in sets];numeric=[x for x in numeric if x[0] is not None]
            best=max(numeric,key=lambda x:x[0])[1] if numeric else None
            suffix=f" • máx {_row(best,'load')} × {_row(best,'reps') or '-'}" if best else ""
            out.append(f"• {name}: {values}{suffix}")
    return "\n".join(out)

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    n=app.norm(text)
    if n not in ("historico de cargas","historico cargas","cargas anteriores","meu historico de treino","progresso de cargas") and text!=HISTORY_BUTTON:
        return False
    user=await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    if not user:return False
    uid=int(_row(user,"id"))
    await send_message(token,int(chat_id),await _history_text(db,uid),reply_markup=app.kb(app.WORKOUT_KB))
    return True


def install():
    app.workout_plan=workout_plan_with_cardio
    app.workout_text=workout_text_with_references
    # Mantém os botões existentes e acrescenta consulta detalhada de histórico.
    if not any(HISTORY_BUTTON in row for row in app.WORKOUT_KB):
        app.WORKOUT_KB.insert(-1,[HISTORY_BUTTON])
