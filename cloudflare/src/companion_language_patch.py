import re

import academic_intelligence as ai
import companion_nlu_v2 as v2
from telegram_api import send_message

WORD_NUMBERS={"uma":1,"um":1,"duas":2,"dois":2,"tres":3,"três":3,"quatro":4}

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip(); n=v2._norm(text)
    if "prova" not in n or not ("duas" in n or "2" in n):return False
    if "mesmo dia" not in n and "nao sei o que fazer" not in n and "não sei o que fazer" not in text.lower():return False
    m=re.search(r"daqui a (uma|um|duas|dois|tres|quatro|\d+) semanas?",n)
    if not m:return False
    token_weeks=m.group(1); weeks=int(token_weeks) if token_weeks.isdigit() else WORD_NUMBERS.get(token_weeks)
    if not weeks:return False
    due=ai._now().date()+ai.timedelta(days=7*weeks)
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    await v2._save_state(db,uid,"collect_exam_subjects",{"due_date":due.isoformat()})
    await send_message(token,int(chat_id),f"Duas provas no mesmo dia em {due.strftime('%d/%m')} dá para organizar sem fazer culto ao desespero. Quais são as duas matérias? Se estiverem cadastradas, eu reconheço e te proponho um plano — sem criar nada antes de você confirmar.")
    return True
