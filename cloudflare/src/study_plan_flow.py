"""Fluxo genérico de sugestão para duas provas próximas.

A sugestão pode montar uma proposta; só após confirmação grava provas/blocos de estudo.
Usa matérias do próprio user_id.
"""
from datetime import date, timedelta

import academic_intelligence as ai
import companion_nlu_v2 as v2
from core_actions import create_task
from telegram_api import send_message


def _row(row,key,default=None):
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default

async def _rows(stmt):
    result=await stmt.all(); data=getattr(result,"results",None)
    if data is None:return []
    try:return list(data)
    except Exception:return data.to_py() if hasattr(data,"to_py") else []

async def _subject_matches(db,uid,text):
    subjects=await _rows(db.prepare("SELECT id,name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid)); n=v2._norm(text); matches=[]
    for subject in subjects:
        name=v2._norm(_row(subject,"name") or ""); tokens=[t for t in name.split() if len(t)>=4]
        if name and (name in n or any(t in n for t in tokens)):matches.append(subject)
    unique=[]; ids=set()
    for subject in matches:
        sid=int(_row(subject,"id"))
        if sid not in ids:ids.add(sid); unique.append(subject)
    return unique,subjects

async def _create_exam_plan(db,uid,payload):
    due=date.fromisoformat(payload["due_date"]); subjects=[]
    for sid in payload.get("subject_ids",[]):
        subject=await db.prepare("SELECT id,name FROM subjects WHERE id=? AND user_id=?").bind(sid,uid).first()
        if subject:subjects.append(subject)
    if len(subjects)<2:return 0,0

    exams=0
    for subject in subjects:
        detail=f"exam:{_row(subject,'id')}"
        exists=await db.prepare("SELECT id FROM daily_items WHERE user_id=? AND details=? AND due_date=? AND status='pendente' LIMIT 1").bind(uid,detail,due.isoformat()).first()
        if not exists:
            await ai._save_exam(db,uid,subject,due,None); exams+=1

    start=ai._now().date()+timedelta(days=1); total_days=max((due-start).days,0); created=0
    for offset in range(total_days):
        d=start+timedelta(days=offset)
        if d>=due:break
        subject=subjects[offset%len(subjects)]; remaining=(due-d).days
        if remaining<=2:stage="revisão ativa + questões-chave"
        elif remaining<=max(4,total_days//3):stage="exercícios e correção dos erros"
        else:stage="teoria + resumo curto"
        title=f"Estudo — {_row(subject,'name')}: {stage}"; details=f"study-plan:{_row(subject,'id')}:{due.isoformat()}"
        exists=await db.prepare("SELECT id FROM daily_items WHERE user_id=? AND details=? AND due_date=? LIMIT 1").bind(uid,details,d.isoformat()).first()
        if not exists:
            if await create_task(db,uid,title,d.isoformat(),None,details):created+=1
    return exams,created

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text:return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    state=await v2._last_state(db,uid)
    if not state:return False
    kind=state.get("kind"); payload=state.get("payload") or {}; n=v2._norm(text)

    # Estados de coleta nunca podem sequestrar comandos globais de saída.
    # Day-off precisa ser tratado pelo dispatcher global; cancelamentos simples
    # encerram este wizard imediatamente.
    if kind in ("collect_exam_subjects","confirm_exam_plan"):
        if n in ("day off","dayoff"):
            await v2._save_state(db,uid,"idle",{})
            return False
        if v2._is_no(n) or n in ("cancelar","cancelar plano","sair","voltar"):
            await v2._save_state(db,uid,"idle",{})
            await send_message(token,int(chat_id),"Fechado. Cancelei esse plano e saí desse fluxo.")
            return True

    if kind=="collect_exam_subjects":
        matches,subjects=await _subject_matches(db,uid,text)
        if len(matches)<2:
            names="\n".join(f"• {_row(s,'name')}" for s in subjects[:12])
            await send_message(token,int(chat_id),"Ainda não consegui identificar duas matérias cadastradas nessa frase. Me manda os dois nomes.\n\nAtivas:\n"+names)
            return True
        chosen=matches[:2]; proposal={"due_date":payload["due_date"],"subject_ids":[int(_row(s,"id")) for s in chosen],"subjects":[_row(s,"name") for s in chosen]}
        await v2._save_state(db,uid,"confirm_exam_plan",proposal)
        await send_message(token,int(chat_id),f"Beleza: {_row(chosen[0],'name')} e {_row(chosen[1],'name')} em {date.fromisoformat(payload['due_date']).strftime('%d/%m')}. Posso cadastrar as provas que faltarem e distribuir blocos de teoria/resumo, exercícios e revisão até lá?")
        return True

    if kind=="confirm_exam_plan" and (v2._is_yes(n) or v2._is_no(n)):
        if v2._is_no(n):
            await v2._save_state(db,uid,"idle",{}); await send_message(token,int(chat_id),"Fechado. Não mexi em nada. O caos continua artesanal."); return True
        exams,tasks=await _create_exam_plan(db,uid,payload); await v2._save_state(db,uid,"idle",{})
        await send_message(token,int(chat_id),f"Pronto. Cadastrei {exams} prova(s) que faltavam e {tasks} bloco(s) de estudo até {date.fromisoformat(payload['due_date']).strftime('%d/%m')}. O plano alterna conteúdo, exercício e revisão.")
        return True
    return False
