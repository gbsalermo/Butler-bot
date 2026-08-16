"""Liga handlers legados da Library ao contexto curto central.

Não responde nem executa ações. Depois que algum handler da Library resolve a
mensagem, registra o assunto mais provável na memória operacional por usuário.
"""
import companion_nlu_v2 as v2
from context_memory import remember_topic
from library_index import search

async def remember_library_reply(db,chat_id,route,text):
    uid=await v2._uid(db,int(chat_id))
    if not uid:return

    domain=route.domain
    target=route.target
    meta={"source":"library","intent":route.intent}

    if domain=="cooking":
        await remember_topic(db,uid,"cooking",target,meta)
        return

    lookup_domain=domain if domain in {"games","books","movies_series","culture"} else None
    results=search(text,domain=lookup_domain,limit=1)
    if results:
        rec=results[0]
        await remember_topic(db,uid,rec["domain"],rec["name"],meta)
    elif domain not in ("conversation",None):
        await remember_topic(db,uid,domain,target,meta)
