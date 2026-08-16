import json
import re
import unicodedata


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


async def _rows(stmt):
    result = await stmt.all()
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


def _norm(text):
    value = unicodedata.normalize("NFKD", (text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _terms(text):
    stop = {"a","o","as","os","de","da","do","das","dos","e","em","um","uma","pra","para","que","eu","meu","minha","to","ta","tô","tá","com","por","isso","esse","essa","ele","ela"}
    return {x for x in _norm(text).split() if len(x) >= 3 and x not in stop}


async def relevant_memories(db, uid, message, limit=6):
    """Busca memória persistida por relevância lexical + importância, sem reenviar o histórico inteiro."""
    rs = await _rows(db.prepare(
        "SELECT id,detail,created_at FROM natural_events WHERE user_id=? AND event_type='llm_memory' ORDER BY id DESC LIMIT 80"
    ).bind(uid))
    wanted = _terms(message)
    ranked = []
    for r in rs:
        try:
            data = json.loads(_row(r, "detail") or "{}")
        except Exception:
            continue
        fact = str(data.get("fact") or "").strip()
        if not fact:
            continue
        tags = data.get("tags") or []
        haystack = fact + " " + " ".join(str(x) for x in tags)
        overlap = len(wanted & _terms(haystack))
        kind = data.get("type") or "episodic"
        importance = float(data.get("importance", data.get("confidence", 0.5)) or 0.5)
        # Stable/preferences may remain useful even with weak lexical overlap; episodes need a stronger match.
        score = overlap * 3 + importance + (0.35 if kind in ("stable", "behavioral") else 0)
        if overlap or kind in ("stable", "behavioral"):
            ranked.append((score, int(_row(r, "id", 0)), {
                "type": kind,
                "subject": data.get("subject"),
                "fact": fact,
                "tags": tags[:6] if isinstance(tags, list) else [],
            }))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [item[2] for item in ranked[:limit]]


async def recent_turns(db, uid, limit=4):
    rs = await _rows(db.prepare(
        "SELECT detail FROM natural_events WHERE user_id=? AND event_type='llm_turn' ORDER BY id DESC LIMIT ?"
    ).bind(uid, limit))
    turns = []
    for r in reversed(rs):
        try:
            data = json.loads(_row(r, "detail") or "{}")
        except Exception:
            continue
        if data.get("user") and data.get("assistant"):
            turns.append({"user": data["user"][:420], "assistant": data["assistant"][:520]})
    return turns


async def save_candidates(db, uid, candidates):
    """Persiste só o essencial. Deduplica por fato normalizado e atualiza confiança/metadata quando reaparece."""
    if not isinstance(candidates, list):
        return
    existing_rows = await _rows(db.prepare(
        "SELECT id,detail FROM natural_events WHERE user_id=? AND event_type='llm_memory' ORDER BY id DESC LIMIT 120"
    ).bind(uid))
    existing = []
    for row in existing_rows:
        try:
            data = json.loads(_row(row, "detail") or "{}")
        except Exception:
            continue
        fact = str(data.get("fact") or "").strip()
        if fact:
            existing.append((int(_row(row, "id", 0)), _norm(fact), data))

    for candidate in candidates[:4]:
        if not isinstance(candidate, dict):
            continue
        kind = candidate.get("type")
        fact = str(candidate.get("fact") or "").strip()
        try:
            confidence = float(candidate.get("confidence", 0))
        except Exception:
            confidence = 0
        threshold = 0.92 if kind == "stable" else 0.86
        if kind not in ("stable", "episodic", "behavioral") or confidence < threshold or len(fact) < 8 or len(fact) > 280:
            continue
        normalized = _norm(fact)
        duplicate = next((x for x in existing if x[1] == normalized), None)
        tags = candidate.get("tags") if isinstance(candidate.get("tags"), list) else []
        subject = str(candidate.get("subject") or "").strip()[:80] or None
        importance = candidate.get("importance", confidence)
        try:
            importance = max(0.0, min(1.0, float(importance)))
        except Exception:
            importance = confidence
        detail = {
            "type": kind,
            "subject": subject,
            "fact": fact,
            "tags": [str(x).strip()[:40] for x in tags[:8] if str(x).strip()],
            "confidence": round(confidence, 3),
            "importance": round(importance, 3),
        }
        if duplicate:
            event_id, _, old = duplicate
            # Reaparecer reforça a memória, sem criar cópias nem chamar a LLM para redescobrir depois.
            if float(old.get("confidence", 0) or 0) <= confidence:
                await db.prepare("UPDATE natural_events SET detail=? WHERE id=?").bind(json.dumps(detail, ensure_ascii=False), event_id).run()
            continue
        await db.prepare("INSERT INTO natural_events(user_id,event_type,detail) VALUES(?,'llm_memory',?)").bind(uid, json.dumps(detail, ensure_ascii=False)).run()
        existing.append((0, normalized, detail))
