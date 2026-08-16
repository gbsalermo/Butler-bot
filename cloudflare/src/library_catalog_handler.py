"""Fallback data-driven da Butler Library.

Roda apenas depois dos handlers específicos e nunca em mensagens de Core. Serve para
variações de consulta/recomendação que não merecem um novo if por entidade.
"""
import companion_nlu_v2 as v2
from context_memory import remember_topic
from context_router import classify
from library_index import search
from telegram_api import send_message

RECOMMEND_WORDS=("indica","recomenda","sugere","quero um","quero uma","algo","alguma coisa")
INFO_WORDS=("quem e","quem foi","o que e","me fala","fala sobre","me explica","sobre o que","do que fala")

async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    route=classify(text)
    if route.tier=="core" or route.domain in ("conversation","cooking"):return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=route.normalized
    domain=route.domain if route.domain in ("games","books","movies_series","culture") else None
    results=search(text,domain=domain,limit=5)
    if not results:return False

    wants_info=any(x in n for x in INFO_WORDS)
    wants_recommend=any(x in n for x in RECOMMEND_WORDS) or route.intent.startswith("recommend_")
    top=results[0]

    # Entidade muito bem recuperada: resposta direta.
    if wants_info or (not wants_recommend and any(alias.lower() in text.lower() for alias in top.get("aliases",[]) if alias)):
        await remember_topic(db,uid,top["domain"],top["name"],{"source":"library_index"})
        await send_message(token,int(chat_id),f"{top['name'].title()} — {top.get('summary') or 'Tenho a referência no acervo, mas ainda sem resumo suficiente.'}")
        return True

    if wants_recommend:
        lines=[]
        for rec in results[:5]:
            summary=(rec.get("summary") or "").strip()
            lines.append(f"• {rec['name'].title()}"+(f" — {summary}" if summary else ""))
        if lines:
            await remember_topic(db,uid,results[0]["domain"],results[0]["name"],{"source":"library_index","recommendation":True})
            await send_message(token,int(chat_id),"Eu procuraria por aqui:\n\n"+"\n".join(lines))
            return True
    return False
