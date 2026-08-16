"""Edição de rotinas e checkpoints.

Permite editar horários sem recriar a rotina. A rotina continua sendo a mesma
entidade; somente os campos escolhidos são alterados. Logs históricos não são apagados.
"""
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import runtime_guard
from settings import UTC_OFFSET_HOURS
from telegram_api import send_message

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
ROUTINE_EDIT_KB=[
    ["➕ Adicionar horário","➖ Remover horário"],
    ["🕐 Alterar horário","✏️ Renomear rotina"],
    ["⬅️ Voltar às rotinas"],
]
CANCEL_KB=[["❌ Cancelar ação"]]


def _kb(rows):return {"keyboard":rows,"resize_keyboard":True}
def _norm(text):
    v=unicodedata.normalize("NFKD",(text or "").lower());v="".join(c for c in v if not unicodedata.combining(c));return re.sub(r"[^a-z0-9:# ]+"," ",v).strip()
def _row(row,key,default=None):
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default
async def _rows(stmt):
    r=await stmt.all();data=getattr(r,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []
def _times(value):return list(dict.fromkeys(re.findall(r"\b(?:[01]\d|2[0-3]):[0-5]\d\b",value or "")))
def _parse_times(text):
    out=[]
    for h,m in re.findall(r"\b([01]?\d|2[0-3])(?::|h)([0-5]\d)?\b",_norm(text)):
        out.append(f"{int(h):02d}:{int(m or 0):02d}")
    return list(dict.fromkeys(out))
def _format(r):
    times=_times(_row(r,"time_hhmm"));when=" • ".join(times) if times else "sem horário"
    return f"🧘 {_row(r,'name')}\nHorários: {when}\nDias: {_row(r,'weekdays') or 'todos os dias'}\nMeta: {_row(r,'category') or '—'}"

def _edit_help():
    return (
        "O que quer alterar?\n\n"
        "➕ Adicionar horário — ex.: `adicionar horário`\n"
        "➖ Remover horário — ex.: `remover horário`\n"
        "🕐 Alterar horário — ex.: `mudar horário`\n"
        "✏️ Renomear rotina — ex.: `renomear rotina`\n\n"
        "Pode usar os botões ou escrever do seu jeito."
    )

async def _find(db,uid,text):
    m=re.search(r"#?(\d+)",text or "")
    if m:
        r=await db.prepare("SELECT * FROM routines WHERE id=? AND user_id=? AND active=1").bind(int(m.group(1)),uid).first()
        if r:return r
    n=_norm(text);rs=await _rows(db.prepare("SELECT * FROM routines WHERE user_id=? AND active=1").bind(uid));matches=[]
    for r in rs:
        name=_norm(_row(r,"name") or "")
        if name and (name in n or n in name):matches.append(r)
    return matches[0] if len(matches)==1 else None

async def _today_done(db,rid,old_times):
    """Lê o progresso de hoje usando os horários ANTERIORES à edição.

    O status legado `feito` quer dizer que todos os checkpoints que existiam naquele
    momento foram cumpridos. Ele não pode significar automaticamente que horários
    adicionados depois também foram feitos.
    """
    today=datetime.now(timezone.utc).astimezone(LOCAL_TZ).date().isoformat()
    row=await db.prepare("SELECT status FROM routine_logs WHERE routine_id=? AND log_date=?").bind(rid,today).first()
    if not row:return set(),False
    status=_row(row,"status") or ""
    if status=="feito":return set(old_times),True
    try:
        payload=json.loads(status)
        return set(payload.get("done") or []),True
    except Exception:
        return set(),True

async def _reconcile_today_log(db,rid,old_times,new_times):
    """Preserva só checkpoints realmente concluídos após uma edição de horários."""
    done,exists=await _today_done(db,rid,old_times)
    if not exists:return
    kept=sorted(t for t in done if t in set(new_times))
    today=datetime.now(timezone.utc).astimezone(LOCAL_TZ).date().isoformat()
    if new_times and all(t in kept for t in new_times):
        status="feito"
    else:
        status=json.dumps({"done":kept,"total":sorted(new_times)},ensure_ascii=False)
    await db.prepare("UPDATE routine_logs SET status=? WHERE routine_id=? AND log_date=?").bind(status,rid,today).run()

async def _save_times(db,uid,rid,times):
    old=await db.prepare("SELECT time_hhmm FROM routines WHERE id=? AND user_id=? AND active=1").bind(rid,uid).first()
    old_times=_times(_row(old,"time_hhmm")) if old else []
    new_times=sorted(set(times))
    value=",".join(new_times) if new_times else None
    await db.prepare("UPDATE routines SET time_hhmm=? WHERE id=? AND user_id=? AND active=1").bind(value,rid,uid).run()
    await _reconcile_today_log(db,rid,old_times,new_times)

async def _show_list(db,token,chat,uid,prompt="Qual rotina quer editar?\nMande o número, #ID ou o nome da rotina."):
    rs=await _rows(db.prepare("SELECT id,name,time_hhmm,weekdays,category FROM routines WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    if not rs:
        await send_message(token,chat,"🧘 Você não tem rotinas ativas.");return
    lines=["🧘 Rotinas"]
    for r in rs:
        ts=" • ".join(_times(_row(r,"time_hhmm"))) or "sem horário";lines.append(f"• #{_row(r,'id')} {_row(r,'name')} — {ts}")
    lines.append("\n"+prompt);await send_message(token,chat,"\n".join(lines),reply_markup=_kb(CANCEL_KB))

async def _open_edit_menu(db,token,chat,uid,routine):
    rid=int(_row(routine,"id"))
    await runtime_guard._set_state(db,uid,"guard_routine_edit_menu",{"id":rid})
    await send_message(token,chat,_format(routine)+"\n\n"+_edit_help(),reply_markup=_kb(ROUTINE_EDIT_KB))

async def handle_message(db,token,message):
    chat=(message.get("chat") or {}).get("id");text=(message.get("text") or "").strip()
    if chat is None or not text:return False
    chat=int(chat);uid=await runtime_guard._uid(db,chat)
    if not uid:return False
    state,payload=await runtime_guard._state(db,uid);n=_norm(text)

    if text=="✏️ Editar rotina" or re.match(r"^(editar|edita)\s+(a\s+)?rotina\b",n):
        routine=await _find(db,uid,re.sub(r"^(editar|edita)\s+(a\s+)?rotina\s*","",text,flags=re.I))
        if routine:
            await _open_edit_menu(db,token,chat,uid,routine);return True
        await runtime_guard._set_state(db,uid,"guard_routine_edit_pick",{});await _show_list(db,token,chat,uid);return True

    direct=re.match(r"^(?:adiciona|adicionar|coloca|bota)\s+(.+?)\s+(?:na|à|a)\s+rotina\s+(?:de\s+)?(.+)$",text,re.I)
    if direct:
        times=_parse_times(direct.group(1));routine=await _find(db,uid,direct.group(2))
        if routine and times:
            current=_times(_row(routine,"time_hhmm"));await _save_times(db,uid,int(_row(routine,"id")),current+times);fresh=await db.prepare("SELECT * FROM routines WHERE id=?").bind(int(_row(routine,"id"))).first();await send_message(token,chat,"✅ Horário adicionado.\n\n"+_format(fresh),reply_markup=_kb(ROUTINE_EDIT_KB));return True
    direct=re.match(r"^(?:remove|remover|tira)\s+(.+?)\s+(?:da|de)\s+rotina\s+(?:de\s+)?(.+)$",text,re.I)
    if direct:
        times=_parse_times(direct.group(1));routine=await _find(db,uid,direct.group(2))
        if routine and times:
            current=[t for t in _times(_row(routine,"time_hhmm")) if t not in times];await _save_times(db,uid,int(_row(routine,"id")),current);fresh=await db.prepare("SELECT * FROM routines WHERE id=?").bind(int(_row(routine,"id"))).first();await send_message(token,chat,"➖ Horário removido.\n\n"+_format(fresh),reply_markup=_kb(ROUTINE_EDIT_KB));return True
    direct=re.match(r"^(?:troca|trocar|muda|mudar)\s+(.+?)\s+(?:por|para)\s+(.+?)\s+(?:na|da|de)\s+rotina\s+(?:de\s+)?(.+)$",text,re.I)
    if direct:
        old=_parse_times(direct.group(1));new=_parse_times(direct.group(2));routine=await _find(db,uid,direct.group(3))
        if routine and old and new:
            current=[t for t in _times(_row(routine,"time_hhmm")) if t not in old]+new;await _save_times(db,uid,int(_row(routine,"id")),current);fresh=await db.prepare("SELECT * FROM routines WHERE id=?").bind(int(_row(routine,"id"))).first();await send_message(token,chat,"🕐 Horário alterado.\n\n"+_format(fresh),reply_markup=_kb(ROUTINE_EDIT_KB));return True

    if state=="guard_routine_edit_pick":
        routine=await _find(db,uid,text)
        if not routine:
            await _show_list(db,token,chat,uid,"Não identifiquei essa. Mande o número, #ID ou o nome.");return True
        await _open_edit_menu(db,token,chat,uid,routine);return True

    if state=="guard_routine_edit_menu":
        rid=payload.get("id");routine=await db.prepare("SELECT * FROM routines WHERE id=? AND user_id=? AND active=1").bind(rid,uid).first()
        if not routine:
            await runtime_guard._clear(db,uid);return False

        add_cmd = text=="➕ Adicionar horário" or n in {"adicionar horario","adiciona horario","add horario","novo horario","colocar horario","bota horario"}
        remove_cmd = text=="➖ Remover horário" or n in {"remover horario","remove horario","tirar horario","tira horario","excluir horario","apagar horario"}
        replace_cmd = text=="🕐 Alterar horário" or n in {"alterar horario","mudar horario","muda horario","trocar horario","troca horario","editar horario"}
        rename_cmd = text=="✏️ Renomear rotina" or n in {"renomear rotina","renomeia rotina","mudar nome","muda nome","alterar nome","editar nome"}
        back_cmd = text=="⬅️ Voltar às rotinas" or n in {"voltar as rotinas","voltar rotinas","voltar"}

        if add_cmd:
            await runtime_guard._set_state(db,uid,"guard_routine_edit_add",{"id":rid});await send_message(token,chat,"Qual horário quer adicionar? Ex.: `17h`, `17:30` ou até `17h e 19h`.",reply_markup=_kb(CANCEL_KB));return True
        if remove_cmd:
            await runtime_guard._set_state(db,uid,"guard_routine_edit_remove",{"id":rid});await send_message(token,chat,_format(routine)+"\n\nQual horário quer remover? Ex.: `17h`.",reply_markup=_kb(CANCEL_KB));return True
        if replace_cmd:
            await runtime_guard._set_state(db,uid,"guard_routine_edit_replace",{"id":rid});await send_message(token,chat,_format(routine)+"\n\nQual troca quer fazer? Ex.: `15h por 16h`.",reply_markup=_kb(CANCEL_KB));return True
        if rename_cmd:
            await runtime_guard._set_state(db,uid,"guard_routine_edit_rename",{"id":rid});await send_message(token,chat,"Qual o novo nome da rotina?",reply_markup=_kb(CANCEL_KB));return True
        if back_cmd:
            await runtime_guard._clear(db,uid);await _show_list(db,token,chat,uid,"Use `editar rotina #ID` quando quiser alterar uma.");return True

        await send_message(token,chat,"Não entendi qual edição você quer.\n\n"+_edit_help(),reply_markup=_kb(ROUTINE_EDIT_KB));return True

    if state in ("guard_routine_edit_add","guard_routine_edit_remove","guard_routine_edit_replace","guard_routine_edit_rename"):
        rid=payload.get("id");routine=await db.prepare("SELECT * FROM routines WHERE id=? AND user_id=? AND active=1").bind(rid,uid).first()
        if not routine:return False
        if n in {"cancelar","cancelar acao"} or text=="❌ Cancelar ação":
            await _open_edit_menu(db,token,chat,uid,routine);return True
        current=_times(_row(routine,"time_hhmm"))
        if state=="guard_routine_edit_rename":
            if not text:return True
            await db.prepare("UPDATE routines SET name=? WHERE id=? AND user_id=?").bind(text,rid,uid).run();msg="✏️ Rotina renomeada."
        elif state=="guard_routine_edit_replace":
            parts=re.split(r"\s+(?:por|para)\s+",text,maxsplit=1,flags=re.I)
            if len(parts)!=2 or not _parse_times(parts[0]) or not _parse_times(parts[1]):
                await send_message(token,chat,"Use algo como `15h por 16h`.",reply_markup=_kb(CANCEL_KB));return True
            old=_parse_times(parts[0]);new=_parse_times(parts[1]);await _save_times(db,uid,rid,[t for t in current if t not in old]+new);msg="🕐 Horário alterado."
        else:
            chosen=_parse_times(text)
            if not chosen:
                await send_message(token,chat,"Não identifiquei horário. Ex.: `17h` ou `17:30`.",reply_markup=_kb(CANCEL_KB));return True
            if state=="guard_routine_edit_add":await _save_times(db,uid,rid,current+chosen);msg="✅ Horário adicionado."
            else:await _save_times(db,uid,rid,[t for t in current if t not in chosen]);msg="➖ Horário removido."
        fresh=await db.prepare("SELECT * FROM routines WHERE id=? AND user_id=?").bind(rid,uid).first();await runtime_guard._set_state(db,uid,"guard_routine_edit_menu",{"id":rid});await send_message(token,chat,msg+"\n\n"+_format(fresh)+"\n\n"+_edit_help(),reply_markup=_kb(ROUTINE_EDIT_KB));return True
    return False
