"""Sugestões transversais do Butler.

Propõe primeiro. Escrita só ocorre após confirmação e passa pelo Core gateway.
"""
import re

import academic_intelligence as ai
import companion_nlu_v2 as v2
from core_actions import add_grocery_items
from language_context import normalize_informal
from telegram_api import send_message

YES={"sim","pode","pode sim","bora","faz","faz isso","manda","manda ver","confirma"}
NO={"nao","não","deixa","deixa quieto","cancela","melhor nao","melhor não"}
OTHER_DOMAIN_WORDS={"aula","materia","prova","treino","dinheiro","tempo","sono","energia","vontade","trabalho","faculdade","rotina"}

async def _handle_pending(db,token,chat_id,uid,text,n):
    state=await v2._last_state(db,uid)
    if not state:return False
    kind=state.get("kind"); payload=state.get("payload") or {}

    if kind=="collect_exam_date":
        due=ai._date_from_phrase(text,ai._now().date())
        if not due or due<ai._now().date():return False
        await v2._save_state(db,uid,"collect_exam_subjects",{"due_date":due.isoformat()})
        await send_message(token,chat_id,f"Fechado, {due.strftime('%d/%m')}. Quais são as duas matérias? Depois eu mostro o plano e só salvo com sua confirmação.")
        return True

    if kind=="suggest_grocery_item" and (n in YES or n in NO):
        if n in NO:
            await v2._save_state(db,uid,"idle",{})
            await send_message(token,chat_id,"Beleza. Era comentário, não ordem de serviço. Não mexi na lista.")
            return True
        item=str(payload.get("item") or "").strip()
        saved=await add_grocery_items(db,uid,[item])
        await v2._save_state(db,uid,"idle",{})
        if saved:await send_message(token,chat_id,f"Pronto. {saved[0]} entrou na lista de itens faltando.")
        else:await send_message(token,chat_id,"Não consegui validar o item, então não salvei nada.")
        return True
    return False

def _household_shortage(n):
    if any(word in n for word in OTHER_DOMAIN_WORDS):return None
    patterns=(
        r"^(?:acabou|cabou) (?:o |a )?(.+)$",
        r"^(.+?) (?:acabou|acabaram|esta acabando|ta acabando)$",
        r"^(?:estou sem|to sem) (.+)$",
        r"^(.+?) (?:nao tem mais|nao temos mais)$",
    )
    for pattern in patterns:
        m=re.match(pattern,n)
        if m:
            item=m.group(1).strip(" .,!?")[:80]
            if 1<len(item)<=80:return item
    return None

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text:return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=normalize_informal(text)
    if await _handle_pending(db,token,int(chat_id),uid,text,n):return True

    if "prova" in n and ("duas" in n or re.search(r"\b2\b",n)) and any(x in n for x in ("mesmo dia","nao sei o que fazer","estou perdido","to perdido","complicado")):
        due=ai._date_from_phrase(text,ai._now().date())
        if due and due>=ai._now().date():
            await v2._save_state(db,uid,"collect_exam_subjects",{"due_date":due.isoformat()})
            await send_message(token,int(chat_id),f"Duas provas em {due.strftime('%d/%m')} merecem plano antes de merecer desespero. Quais são as duas matérias? Eu monto a proposta e só salvo se você confirmar.")
            return True
        await v2._save_state(db,uid,"collect_exam_date",{})
        await send_message(token,int(chat_id),"Duas provas no mesmo dia dá para organizar. Que dia elas são? Depois eu peço as matérias e te mostro um plano antes de salvar qualquer coisa.")
        return True

    item=_household_shortage(n)
    if item:
        await v2._save_state(db,uid,"suggest_grocery_item",{"item":item})
        await send_message(token,int(chat_id),f"Quer que eu coloque {item} na lista de itens faltando? Se foi só comentário, manda `deixa`; se quiser salvar, `pode`.")
        return True
    return False
