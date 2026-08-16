"""Contexto recente curto e isolado por usuário.

Memória operacional, não memória pessoal permanente. Mantém poucos tópicos para
resolver follow-ups sem deixar um assunto antigo sequestrar mensagens futuras.
"""
import json
from datetime import datetime, timezone

MAX_TOPICS=3
_SCHEMA_READY=False

def _row(row,key,default=None):
    if row is None:return default
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default

async def ensure_schema(db):
    global _SCHEMA_READY
    if _SCHEMA_READY:return
    await db.prepare("""CREATE TABLE IF NOT EXISTS conversation_context (
      user_id INTEGER PRIMARY KEY,
      topics_json TEXT NOT NULL DEFAULT '[]',
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""").run()
    _SCHEMA_READY=True

async def get_topics(db,user_id):
    await ensure_schema(db)
    row=await db.prepare("SELECT topics_json FROM conversation_context WHERE user_id=?").bind(user_id).first()
    if not row:return []
    try:return json.loads(_row(row,"topics_json") or "[]")[:MAX_TOPICS]
    except Exception:return []

async def remember_topic(db,user_id,domain,target=None,meta=None):
    await ensure_schema(db)
    topics=await get_topics(db,user_id)
    item={"domain":domain,"target":target,"meta":meta or {},"at":datetime.now(timezone.utc).isoformat()}
    topics=[item]+[x for x in topics if not (x.get("domain")==domain and x.get("target")==target)]
    topics=topics[:MAX_TOPICS]
    payload=json.dumps(topics,ensure_ascii=False); now=datetime.now(timezone.utc).isoformat()
    await db.prepare("""INSERT INTO conversation_context(user_id,topics_json,updated_at) VALUES(?,?,?)
      ON CONFLICT(user_id) DO UPDATE SET topics_json=excluded.topics_json, updated_at=excluded.updated_at""").bind(user_id,payload,now).run()

async def current_topic(db,user_id,domain=None):
    for topic in await get_topics(db,user_id):
        if domain is None or topic.get("domain")==domain:return topic
    return None

async def clear_domain(db,user_id,domain):
    topics=[x for x in await get_topics(db,user_id) if x.get("domain")!=domain]
    now=datetime.now(timezone.utc).isoformat()
    await db.prepare("UPDATE conversation_context SET topics_json=?, updated_at=? WHERE user_id=?").bind(json.dumps(topics,ensure_ascii=False),now,user_id).run()
