"""Sincroniza o roteador central com contextos legados.

Enquanto módulos antigos ainda usam natural_events para follow-up, uma troca explícita
de domínio grava uma barreira. Assim contexto culinário/série anterior não volta depois.
"""
import json

import companion_nlu_v2 as v2
from context_memory import remember_topic

async def sync_route(db,chat_id,route,text):
    uid=await v2._uid(db,int(chat_id))
    if not uid:return None
    if route.domain!="conversation":
        await remember_topic(db,uid,route.domain,route.target,{"intent":route.intent,"time_hint":route.time_hint,"text":(text or "")[:180]})
    if route.tier=="core":
        detail=json.dumps({"domain":"_invalidated","by":route.domain,"text":(text or "")[:120]},ensure_ascii=False)
        await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'library_context',?)").bind(uid,detail).run()
        await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'library_setup',?)").bind(uid,json.dumps({"kind":"_invalidated","by":route.domain},ensure_ascii=False)).run()
    return uid
