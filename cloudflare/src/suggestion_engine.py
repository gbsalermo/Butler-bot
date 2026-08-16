"""Sugestões transversais do Butler.

Só propõe ações; não grava dados. Escrita continua com os módulos/Core após confirmação.
"""
import re
from datetime import timedelta

import academic_intelligence as ai
import companion_nlu_v2 as v2
from language_context import normalize_informal
from telegram_api import send_message

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text:return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=normalize_informal(text)

    # Sobrecarga acadêmica: oferece organização, sem cadastrar nada ainda.
    if "prova" in n and ("duas" in n or re.search(r"\b2\b",n)) and any(x in n for x in ("mesmo dia","nao sei o que fazer","estou perdido","to perdido","complicado")):
        due=ai._date_from_phrase(text,ai._now().date())
        if due and due>=ai._now().date():
            await v2._save_state(db,uid,"collect_exam_subjects",{"due_date":due.isoformat()})
            await send_message(token,int(chat_id),f"Duas provas em {due.strftime('%d/%m')} merecem plano antes de merecer desespero. Quais são as duas matérias? Eu monto a proposta e só salvo se você confirmar.")
            return True
        await v2._save_state(db,uid,"collect_exam_date",{})
        await send_message(token,int(chat_id),"Duas provas no mesmo dia dá para organizar. Que dia elas são? Depois eu peço as matérias e te mostro um plano antes de salvar qualquer coisa.")
        return True

    # Necessidade de casa dita como problema, sem verbo de comando: sugere mercado.
    if any(x in n for x in ("acabou o ","acabou a ","estou sem ","to sem ")) and not any(x in n for x in ("aula","materia","prova","treino","dinheiro","tempo")):
        m=re.search(r"(?:acabou (?:o|a)|estou sem|to sem)\s+(.+)$",n)
        if m:
            item=m.group(1).strip(" .,!?")[:80]
            if item:
                await v2._save_state(db,uid,"suggest_grocery_item",{"item":item})
                await send_message(token,int(chat_id),f"Quer que eu coloque {item} na lista de itens faltando? Se for só comentário, deixa quieto; se quiser, manda `pode`.")
                return True
    return False
