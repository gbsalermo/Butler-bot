"""Modo Estudo persistente do Butler.

Foco/pausa usam o mesmo ``PersonalAlarm`` dos demais eventos temporais, mas o
domínio de estudo mantém suas próprias regras. Em especial: o fim do timer NUNCA
conclui ou pula um tópico. Progresso só muda por ação explícita do usuário.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re

import app
import language_primitives as language
import quality_patch
from telegram_api import send_message

DEFAULT_FOCUS_MINUTES = 25
DEFAULT_BREAK_MINUTES = 5
DEFAULT_LONG_BREAK_MINUTES = 15
DEFAULT_LONG_BREAK_EVERY = 4

MIN_FOCUS_MINUTES = 5
MAX_FOCUS_MINUTES = 120
MIN_BREAK_MINUTES = 1
MAX_BREAK_MINUTES = 60
MIN_LONG_BREAK_MINUTES = 5
MAX_LONG_BREAK_MINUTES = 90

_SCHEMA_READY = False
_INSTALLED = False

START_PREFIXES = (
    r"^modo\s+estudo\b",
    r"^(?:inicia|inicie|iniciar|comeca|comece|comecar)\s+(?:o\s+)?modo\s+estudo\b",
    r"^(?:quero|vou)\s+estudar\b",
    r"^vamos\s+estudar\b",
)

STATUS_PHRASES = {
    "status estudo", "status do estudo", "como ta o estudo", "como esta o estudo",
    "onde parei no estudo", "modo estudo status", "qual topico do estudo",
}
COMPLETE_PHRASES = {
    "conclui o topico", "concluir o topico", "terminei o topico", "terminei esse topico",
    "finalizei o topico", "topico concluido", "terminei essa parte",
}
SKIP_PHRASES = {
    "pula o topico", "pular topico", "pular o topico", "pula esse topico",
    "ignora esse topico", "quero pular o topico",
}
PAUSE_PHRASES = {
    "pausar estudo", "pausa o estudo", "pausa estudo", "parar estudo por enquanto",
}
RESUME_PHRASES = {
    "retomar estudo", "retoma o estudo", "continuar estudo", "continua o estudo",
    "voltar ao estudo", "volta pro estudo",
}
CANCEL_PHRASES = {
    "cancelar estudo", "cancela o estudo", "encerrar estudo", "parar estudo",
}
NOT_DONE_PHRASES = {
    "nao terminei", "nao terminei o topico", "ainda nao terminei", "nao conclui o topico",
}
HISTORY_PHRASES = {
    "historico de estudo", "historico estudo", "meus estudos", "sessoes de estudo",
}


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


async def ensure_schema(db):
    """Guard defensivo acionado apenas dentro do domínio de estudo.

    A migration 0011 é a fonte formal. O guard apenas evita quebra caso código e
    migration sejam propagados em instantes diferentes.
    """
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            focus_minutes INTEGER NOT NULL DEFAULT 25,
            break_minutes INTEGER NOT NULL DEFAULT 5,
            long_break_minutes INTEGER NOT NULL DEFAULT 15,
            long_break_every INTEGER NOT NULL DEFAULT 4,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','paused','completed','cancelled')),
            phase TEXT NOT NULL DEFAULT 'focus' CHECK(phase IN ('focus','break','long_break','paused','completed','cancelled')),
            phase_ends_at TEXT,
            cycles_completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            cancelled_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_study_sessions_user_status "
        "ON study_sessions(user_id,status,phase_ends_at)"
    ).run()
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS study_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','completed','skipped')),
            completed_at TEXT,
            skipped_at TEXT,
            FOREIGN KEY(session_id) REFERENCES study_sessions(id) ON DELETE CASCADE,
            UNIQUE(session_id, position)
        )
    """).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_study_topics_session_status "
        "ON study_topics(session_id,status,position)"
    ).run()
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS study_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            topic_id INTEGER,
            event_type TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES study_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(topic_id) REFERENCES study_topics(id) ON DELETE SET NULL
        )
    """).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_study_events_session_created "
        "ON study_events(session_id,created_at,id)"
    ).run()
    _SCHEMA_READY = True


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    return int(_row(row, "id")) if row else None


def _now_utc():
    return datetime.now(timezone.utc)


def _parse_iso(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _norm(text):
    return language.normalize_text(language.strip_butler(text))


def is_study_candidate(text):
    n = _norm(text)
    if not n:
        return False
    if any(re.search(pattern, n) for pattern in START_PREFIXES):
        if n.startswith(("quero estudar", "vou estudar", "vamos estudar")):
            return "agora" in n
        return True
    return n in (
        STATUS_PHRASES
        | COMPLETE_PHRASES
        | SKIP_PHRASES
        | PAUSE_PHRASES
        | RESUME_PHRASES
        | CANCEL_PHRASES
        | NOT_DONE_PHRASES
        | HISTORY_PHRASES
    )


def _parse_config(text):
    raw = language.strip_butler(text)
    match = re.search(r"\b(\d{1,3})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{1,2}))?\b", raw)
    focus = int(match.group(1)) if match else DEFAULT_FOCUS_MINUTES
    pause = int(match.group(2)) if match else DEFAULT_BREAK_MINUTES
    long_pause = int(match.group(3)) if match and match.group(3) else DEFAULT_LONG_BREAK_MINUTES
    if not (MIN_FOCUS_MINUTES <= focus <= MAX_FOCUS_MINUTES):
        return None, "O foco precisa ficar entre 5 e 120 minutos."
    if not (MIN_BREAK_MINUTES <= pause <= MAX_BREAK_MINUTES):
        return None, "A pausa precisa ficar entre 1 e 60 minutos."
    if not (MIN_LONG_BREAK_MINUTES <= long_pause <= MAX_LONG_BREAK_MINUTES):
        return None, "A pausa longa precisa ficar entre 5 e 90 minutos."
    return {
        "focus_minutes": focus,
        "break_minutes": pause,
        "long_break_minutes": long_pause,
        "long_break_every": DEFAULT_LONG_BREAK_EVERY,
    }, None


def _parse_topics(text):
    raw = (text or "").strip()
    if not raw:
        return []
    if _norm(raw) in {"sessao livre", "sem topicos", "estudo livre"}:
        return ["Sessão livre"]
    if re.search(r"[,;\n]", raw):
        chunks = [x.strip(" .-–—") for x in re.split(r"[,;\n]+", raw) if x.strip(" .-–—")]
        if chunks and re.search(r"\s+e\s+", chunks[-1], flags=re.I):
            left, right = re.split(r"\s+e\s+", chunks[-1], maxsplit=1, flags=re.I)
            if left.strip() and right.strip():
                chunks[-1:] = [left.strip(), right.strip()]
    else:
        chunks = [raw.strip(" .-–—")]
    out = []
    seen = set()
    for item in chunks:
        item = re.sub(r"\s+", " ", item).strip()
        if not item or len(item) > 120:
            continue
        key = language.normalize_text(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:30]


def _parse_start(text):
    config, error = _parse_config(text)
    if error:
        return {"error": error}
    raw = language.strip_butler(text).strip()
    raw = re.sub(r"\b\d{1,3}\s*/\s*\d{1,2}(?:\s*/\s*\d{1,2})?\b", " ", raw)
    for pattern in (
        r"^modo\s+estudo\b",
        r"^(?:inicia|inicie|iniciar|comeca|começa|comece|comecar|começar)\s+(?:o\s+)?modo\s+estudo\b",
        r"^(?:quero|vou)\s+estudar\b",
        r"^vamos\s+estudar\b",
    ):
        updated = re.sub(pattern, "", raw, flags=re.I).strip()
        if updated != raw:
            raw = updated
            break
    raw = re.sub(r"\bagora\b", " ", raw, flags=re.I)
    raw = re.sub(r"\s+", " ", raw).strip(" ,.-")
    if ":" in raw:
        subject, topics_text = raw.split(":", 1)
        subject = subject.strip(" ,.-")
        topics = _parse_topics(topics_text)
    else:
        subject = raw.strip(" ,.-")
        topics = []
    return {"subject": subject, "topics": topics, **config}


async def _canonical_subject(db, uid, subject):
    subject = re.sub(r"\s+", " ", (subject or "")).strip()
    if not subject:
        return subject
    try:
        rows = await _rows(db.prepare("SELECT name FROM subjects WHERE user_id=? AND active=1 ORDER BY name").bind(uid))
    except Exception:
        return subject
    wanted = language.normalize_text(subject)
    exact = [_row(r, "name") for r in rows if language.normalize_text(_row(r, "name")) == wanted]
    if exact:
        return exact[0]
    matches = [
        _row(r, "name") for r in rows
        if wanted in language.normalize_text(_row(r, "name"))
        or language.normalize_text(_row(r, "name")) in wanted
    ]
    return matches[0] if len(matches) == 1 else subject


async def _active_session(db, uid):
    return await db.prepare(
        "SELECT * FROM study_sessions WHERE user_id=? AND status IN ('active','paused') ORDER BY id DESC LIMIT 1"
    ).bind(int(uid)).first()


async def _current_topic(db, session_id):
    return await db.prepare(
        "SELECT * FROM study_topics WHERE session_id=? AND status='pending' ORDER BY position,id LIMIT 1"
    ).bind(int(session_id)).first()


async def _topics(db, session_id):
    return await _rows(db.prepare("SELECT * FROM study_topics WHERE session_id=? ORDER BY position,id").bind(int(session_id)))


async def _log(db, session_id, event_type, topic_id=None, detail=None):
    await db.prepare(
        "INSERT INTO study_events(session_id,topic_id,event_type,detail) VALUES(?,?,?,?)"
    ).bind(
        int(session_id),
        int(topic_id) if topic_id is not None else None,
        event_type,
        json.dumps(detail or {}, ensure_ascii=False),
    ).run()


async def _create_session(db, uid, subject, topics, config, *, now=None):
    await ensure_schema(db)
    now = now or _now_utc()
    subject = await _canonical_subject(db, uid, subject)
    focus_minutes = int(config["focus_minutes"])
    phase_ends = now + timedelta(minutes=focus_minutes)
    result = await db.prepare(
        "INSERT INTO study_sessions(user_id,subject_name,focus_minutes,break_minutes,long_break_minutes,long_break_every,status,phase,phase_ends_at,cycles_completed,updated_at) "
        "VALUES(?,?,?,?,?,?,'active','focus',?,0,CURRENT_TIMESTAMP)"
    ).bind(
        int(uid), subject, focus_minutes, int(config["break_minutes"]),
        int(config["long_break_minutes"]), int(config["long_break_every"]), phase_ends.isoformat(),
    ).run()
    session_id = None
    meta = getattr(result, "meta", None)
    if meta is not None:
        session_id = getattr(meta, "last_row_id", None)
        if session_id is None:
            try:
                session_id = meta["last_row_id"]
            except Exception:
                pass
    if session_id is None:
        row = await db.prepare("SELECT id FROM study_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1").bind(int(uid)).first()
        session_id = int(_row(row, "id"))
    for pos, title in enumerate(topics, 1):
        await db.prepare(
            "INSERT INTO study_topics(session_id,position,title,status) VALUES(?,?,?,'pending')"
        ).bind(session_id, pos, title).run()
    topic = await _current_topic(db, session_id)
    await _log(db, session_id, "session_started", detail={"subject": subject})
    await _log(db, session_id, "focus_started", int(_row(topic, "id")) if topic else None, {"minutes": focus_minutes})
    return await db.prepare("SELECT * FROM study_sessions WHERE id=?").bind(session_id).first(), topic


def _phase_label(phase):
    return {
        "focus": "foco", "break": "pausa", "long_break": "pausa longa",
        "paused": "pausado", "completed": "concluído", "cancelled": "cancelado",
    }.get(phase, phase or "-")


def _remaining_text(session, *, now=None):
    now = now or _now_utc()
    end = _parse_iso(_row(session, "phase_ends_at"))
    if not end:
        return None
    seconds = max(0, int((end - now).total_seconds()))
    minutes, sec = divmod(seconds, 60)
    return f"{minutes} min {sec:02d}s" if minutes else f"{sec}s"


async def _status_text(db, session, *, now=None):
    sid = int(_row(session, "id"))
    topic = await _current_topic(db, sid)
    rows = await _topics(db, sid)
    completed = sum(_row(r, "status") == "completed" for r in rows)
    skipped = sum(_row(r, "status") == "skipped" for r in rows)
    lines = [
        f"📚 Modo Estudo — {_row(session,'subject_name')}",
        f"• Estado: {_phase_label(_row(session,'phase'))}",
        f"• Tópico atual: {_row(topic,'title') if topic else 'nenhum pendente'}",
        f"• Progresso: {completed} concluído(s), {skipped} pulado(s), {len(rows)-completed-skipped} pendente(s)",
        f"• Ciclo: {_row(session,'focus_minutes')} min foco / {_row(session,'break_minutes')} min pausa / {_row(session,'long_break_minutes')} min pausa longa",
        f"• Blocos de foco encerrados: {int(_row(session,'cycles_completed',0) or 0)}",
    ]
    remaining = _remaining_text(session, now=now)
    if remaining and _row(session, "status") == "active":
        lines.append(f"• Restante desta fase: {remaining}")
    return "\n".join(lines)


async def _set_break_after_focus(db, session, *, now=None, reason="timer", focus_topic_id=None):
    now = now or _now_utc()
    sid = int(_row(session, "id"))
    cycles = int(_row(session, "cycles_completed", 0) or 0) + 1
    every = max(1, int(_row(session, "long_break_every", DEFAULT_LONG_BREAK_EVERY) or DEFAULT_LONG_BREAK_EVERY))
    is_long = cycles % every == 0
    phase = "long_break" if is_long else "break"
    minutes = int(_row(session, "long_break_minutes" if is_long else "break_minutes"))
    ends = now + timedelta(minutes=minutes)
    await db.prepare(
        "UPDATE study_sessions SET cycles_completed=?,phase=?,phase_ends_at=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='active'"
    ).bind(cycles, phase, ends.isoformat(), sid).run()
    current_topic = await _current_topic(db, sid)
    event_topic_id = focus_topic_id if focus_topic_id is not None else (int(_row(current_topic, "id")) if current_topic else None)
    await _log(db, sid, "focus_finished", event_topic_id, {"reason": reason, "cycles_completed": cycles})
    await _log(
        db, sid, "long_break_started" if is_long else "break_started",
        int(_row(current_topic, "id")) if current_topic else None,
        {"minutes": minutes},
    )
    return phase, minutes, current_topic


async def _finish_session_if_empty(db, session_id, *, now=None):
    now = now or _now_utc()
    topic = await _current_topic(db, session_id)
    if topic:
        return False
    current = await db.prepare("SELECT status FROM study_sessions WHERE id=?").bind(int(session_id)).first()
    status = _row(current, "status")
    if status == "completed":
        return True
    if status not in {"active", "paused"}:
        return False
    await db.prepare(
        "UPDATE study_sessions SET status='completed',phase='completed',phase_ends_at=NULL,completed_at=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('active','paused')"
    ).bind(now.isoformat(), int(session_id)).run()
    await _log(db, session_id, "session_completed")
    return True


async def _mark_topic(db, session, action, *, now=None):
    now = now or _now_utc()
    sid = int(_row(session, "id"))
    topic = await _current_topic(db, sid)
    if not topic:
        await _finish_session_if_empty(db, sid, now=now)
        return "✅ Não há tópico pendente nessa sessão."
    topic_id = int(_row(topic, "id"))
    title = _row(topic, "title")
    if action == "completed":
        await db.prepare(
            "UPDATE study_topics SET status='completed',completed_at=? WHERE id=? AND session_id=? AND status='pending'"
        ).bind(now.isoformat(), topic_id, sid).run()
        await _log(db, sid, "topic_completed", topic_id)
        verb = "concluído"
    else:
        await db.prepare(
            "UPDATE study_topics SET status='skipped',skipped_at=? WHERE id=? AND session_id=? AND status='pending'"
        ).bind(now.isoformat(), topic_id, sid).run()
        await _log(db, sid, "topic_skipped", topic_id)
        verb = "pulado"
    if await _finish_session_if_empty(db, sid, now=now):
        return f"✅ {title} {verb}. Todos os tópicos terminaram; sessão concluída."
    next_topic = await _current_topic(db, sid)
    phase = _row(session, "phase")
    if _row(session, "status") == "active" and phase == "focus":
        phase, minutes, _ = await _set_break_after_focus(
            db, session, now=now, reason="explicit_topic_change", focus_topic_id=topic_id
        )
        pause_name = "pausa longa" if phase == "long_break" else "pausa"
        return f"✅ {title} {verb}. Próximo: {_row(next_topic,'title')}. ☕ Começando {pause_name} de {minutes} min antes do próximo foco."
    if phase in {"break", "long_break"}:
        return f"✅ {title} {verb}. Depois da pausa, o próximo foco será {_row(next_topic,'title')}."
    return f"✅ {title} {verb}. Próximo tópico: {_row(next_topic,'title')}."


async def _pause_session(db, session, *, now=None):
    now = now or _now_utc()
    sid = int(_row(session, "id"))
    if _row(session, "status") == "paused":
        return "⏸️ O Modo Estudo já está pausado."
    await db.prepare(
        "UPDATE study_sessions SET status='paused',phase='paused',phase_ends_at=NULL,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='active'"
    ).bind(sid).run()
    await _log(db, sid, "session_paused")
    return "⏸️ Modo Estudo pausado. O tópico continua exatamente onde estava."


async def _resume_session(db, session, *, now=None):
    now = now or _now_utc()
    sid = int(_row(session, "id"))
    if _row(session, "status") != "paused":
        return "📚 A sessão já está rodando."
    topic = await _current_topic(db, sid)
    if not topic:
        await _finish_session_if_empty(db, sid, now=now)
        return "✅ Essa sessão já não tem tópicos pendentes."
    minutes = int(_row(session, "focus_minutes"))
    ends = now + timedelta(minutes=minutes)
    await db.prepare(
        "UPDATE study_sessions SET status='active',phase='focus',phase_ends_at=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='paused'"
    ).bind(ends.isoformat(), sid).run()
    await _log(db, sid, "session_resumed", int(_row(topic, "id")))
    await _log(db, sid, "focus_started", int(_row(topic, "id")), {"minutes": minutes, "reason": "resume"})
    return f"▶️ Voltando: {_row(topic,'title')} — {minutes} min de foco."


async def _cancel_session(db, session, *, now=None):
    now = now or _now_utc()
    sid = int(_row(session, "id"))
    await db.prepare(
        "UPDATE study_sessions SET status='cancelled',phase='cancelled',phase_ends_at=NULL,cancelled_at=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('active','paused')"
    ).bind(now.isoformat(), sid).run()
    await _log(db, sid, "session_cancelled")
    return "⏹️ Modo Estudo encerrado. Nada foi marcado como concluído por isso."


async def _history_text(db, uid):
    sessions = await _rows(
        db.prepare(
            "SELECT id,subject_name,status,cycles_completed,created_at,completed_at,cancelled_at FROM study_sessions WHERE user_id=? ORDER BY id DESC LIMIT 5"
        ).bind(int(uid))
    )
    if not sessions:
        return "📚 Ainda não há sessões de estudo registradas."
    lines = ["📚 Últimas sessões de estudo"]
    for session in sessions:
        topics = await _topics(db, int(_row(session, "id")))
        done = sum(_row(t, "status") == "completed" for t in topics)
        skipped = sum(_row(t, "status") == "skipped" for t in topics)
        lines.append(
            f"• {_row(session,'subject_name')} — {_row(session,'status')} — {done}/{len(topics)} concluído(s), {skipped} pulado(s), {int(_row(session,'cycles_completed',0) or 0)} foco(s) encerrado(s)"
        )
    return "\n".join(lines)


async def _start_or_prompt(db, token, chat_id, uid, text):
    parsed = _parse_start(text)
    if parsed.get("error"):
        await send_message(token, chat_id, f"⏱️ {parsed['error']} Use, por exemplo, `modo estudo 25/5/15 Cálculo: limites, derivadas`.")
        return True
    active = await _active_session(db, uid)
    if active:
        await send_message(token, chat_id, "📚 Já existe uma sessão de estudo aberta. Use `status estudo`, `pausar estudo` ou `cancelar estudo` antes de iniciar outra.")
        return True
    payload = {
        "focus_minutes": parsed["focus_minutes"],
        "break_minutes": parsed["break_minutes"],
        "long_break_minutes": parsed["long_break_minutes"],
        "long_break_every": parsed["long_break_every"],
    }
    subject = parsed.get("subject") or ""
    topics = parsed.get("topics") or []
    if not subject:
        await app.set_state(db, uid, "study_setup_subject", payload)
        await send_message(token, chat_id, "📚 O que você vai estudar? Manda a matéria/assunto.", reply_markup={"keyboard": [["❌ Cancelar ação"]], "resize_keyboard": True})
        return True
    subject = await _canonical_subject(db, uid, subject)
    if not topics:
        await app.set_state(db, uid, "study_setup_topics", {**payload, "subject": subject})
        await send_message(token, chat_id, f"📚 {subject}. Quais tópicos? Separe por vírgulas.\nEx.: `limites, derivadas, integrais`\nOu mande `sessão livre`.", reply_markup={"keyboard": [["❌ Cancelar ação"]], "resize_keyboard": True})
        return True
    session, topic = await _create_session(db, uid, subject, topics, payload)
    await send_message(
        token, chat_id,
        f"📚 Modo Estudo iniciado — {_row(session,'subject_name')}\n🎯 Tópico: {_row(topic,'title')}\n⏱️ {_row(session,'focus_minutes')} min de foco / {_row(session,'break_minutes')} min de pausa.\n\nQuando o foco acabar eu aviso, mas não vou marcar o tópico como concluído sozinho. Diga `concluí o tópico` ou `pular tópico` quando for verdade.",
    )
    return True


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None or not is_study_candidate(text):
        return False
    uid = await _uid(db, int(chat_id))
    if uid is None:
        return False
    await ensure_schema(db)
    n = _norm(text)
    if any(re.search(pattern, n) for pattern in START_PREFIXES):
        return await _start_or_prompt(db, token, int(chat_id), uid, text)
    state, _ = await app.get_state(db, uid)
    if state in {"study_setup_subject", "study_setup_topics"} and n in CANCEL_PHRASES:
        await app.clear_state(db, uid)
        await send_message(token, int(chat_id), "Certo. Configuração do Modo Estudo cancelada.")
        return True
    if n in HISTORY_PHRASES:
        await send_message(token, int(chat_id), await _history_text(db, uid))
        return True
    session = await _active_session(db, uid)
    if not session:
        await send_message(token, int(chat_id), "📚 Não há Modo Estudo ativo agora.")
        return True
    if n in STATUS_PHRASES:
        await send_message(token, int(chat_id), await _status_text(db, session))
        return True
    if n in COMPLETE_PHRASES:
        await send_message(token, int(chat_id), await _mark_topic(db, session, "completed"))
        return True
    if n in SKIP_PHRASES:
        await send_message(token, int(chat_id), await _mark_topic(db, session, "skipped"))
        return True
    if n in PAUSE_PHRASES:
        await send_message(token, int(chat_id), await _pause_session(db, session))
        return True
    if n in RESUME_PHRASES:
        await send_message(token, int(chat_id), await _resume_session(db, session))
        return True
    if n in CANCEL_PHRASES:
        await send_message(token, int(chat_id), await _cancel_session(db, session))
        return True
    if n in NOT_DONE_PHRASES:
        topic = await _current_topic(db, int(_row(session, "id")))
        await send_message(token, int(chat_id), f"📌 {_row(topic,'title') if topic else 'O tópico'} continua pendente. Tempo decorrido não é conclusão; no próximo foco seguimos dele.")
        return True
    return False


async def _advance_due_phase(db, session, *, now=None):
    now = now or _now_utc()
    sid = int(_row(session, "id"))
    phase = _row(session, "phase")
    topic = await _current_topic(db, sid)
    if phase == "focus":
        new_phase, minutes, topic = await _set_break_after_focus(db, session, now=now, reason="timer")
        return {
            "phase": new_phase, "minutes": minutes, "topic": topic,
            "message": f"⏰ Foco encerrado em {_row(session,'subject_name')}" + (f" — {_row(topic,'title')}" if topic else "") + ".\nO relógio acabou; o tópico não. Não marquei nada como concluído.\n" + f"☕ {'Pausa longa' if new_phase == 'long_break' else 'Pausa'} de {minutes} min começando agora.",
        }
    if phase in {"break", "long_break"}:
        if await _finish_session_if_empty(db, sid, now=now):
            return {"phase": "completed", "message": "✅ Sessão de estudo concluída."}
        topic = await _current_topic(db, sid)
        focus = int(_row(session, "focus_minutes"))
        ends = now + timedelta(minutes=focus)
        await db.prepare(
            "UPDATE study_sessions SET phase='focus',phase_ends_at=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='active'"
        ).bind(ends.isoformat(), sid).run()
        await _log(db, sid, "break_finished", int(_row(topic, "id")) if topic else None)
        await _log(db, sid, "focus_started", int(_row(topic, "id")) if topic else None, {"minutes": focus, "reason": "after_break"})
        return {"phase": "focus", "minutes": focus, "topic": topic, "message": f"☕ Pausa acabou. Voltando para {_row(topic,'title')} — {focus} min de foco."}
    return None


async def dispatch_due_study(db, token, user_id=None, *, now=None):
    """Avança fases temporais; nunca altera status de tópico automaticamente."""
    now = now or _now_utc()
    sql = (
        "SELECT s.*,u.telegram_chat_id FROM study_sessions s JOIN users u ON u.id=s.user_id "
        "WHERE s.status='active' AND s.phase IN ('focus','break','long_break') AND s.phase_ends_at IS NOT NULL AND s.phase_ends_at<=?"
    )
    params = [now.isoformat()]
    if user_id is not None:
        sql += " AND s.user_id=?"
        params.append(int(user_id))
    sql += " ORDER BY s.phase_ends_at,s.id LIMIT 100"
    try:
        due = await _rows(db.prepare(sql).bind(*params))
    except Exception:
        return
    for session in due:
        sid = int(_row(session, "id"))
        uid = int(_row(session, "user_id"))
        phase = _row(session, "phase")
        phase_end = _row(session, "phase_ends_at")
        key = f"study:{sid}:{phase}:{phase_end}"
        sent = await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid, key).first()
        if sent:
            await _advance_due_phase(db, session, now=now)
            continue
        if phase == "focus":
            topic = await _current_topic(db, sid)
            cycles = int(_row(session, "cycles_completed", 0) or 0) + 1
            every = max(1, int(_row(session, "long_break_every", DEFAULT_LONG_BREAK_EVERY) or DEFAULT_LONG_BREAK_EVERY))
            is_long = cycles % every == 0
            minutes = int(_row(session, "long_break_minutes" if is_long else "break_minutes"))
            message = f"⏰ Foco encerrado em {_row(session,'subject_name')}" + (f" — {_row(topic,'title')}" if topic else "") + ".\nO relógio acabou; o tópico não. Não marquei nada como concluído.\n" + f"☕ {'Pausa longa' if is_long else 'Pausa'} de {minutes} min começando agora."
        else:
            topic = await _current_topic(db, sid)
            message = f"☕ Pausa acabou. Voltando para {_row(topic,'title')} — {_row(session,'focus_minutes')} min de foco." if topic else "✅ Sessão de estudo concluída."
        await quality_patch.send_message(token, int(_row(session, "telegram_chat_id")), message)
        await db.prepare("INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)").bind(uid, key).run()
        await _advance_due_phase(db, session, now=now)


async def next_study_event(db, uid, *, now=None):
    now = now or _now_utc()
    try:
        row = await db.prepare(
            "SELECT phase_ends_at FROM study_sessions WHERE user_id=? AND status='active' AND phase IN ('focus','break','long_break') AND phase_ends_at IS NOT NULL ORDER BY phase_ends_at,id LIMIT 1"
        ).bind(int(uid)).first()
    except Exception:
        return None
    target = _parse_iso(_row(row, "phase_ends_at")) if row else None
    if target is None:
        return None
    return now + timedelta(seconds=1) if target <= now else target


def install():
    """Acopla apenas os dois passos guiados de setup ao state machine existente."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    original_handle_state = app.handle_state

    async def handle_state_with_study(db, token, chat, uid, owner, state, payload, message):
        if state not in {"study_setup_subject", "study_setup_topics"}:
            return await original_handle_state(db, token, chat, uid, owner, state, payload, message)
        text = (message.get("text") or "").strip()
        n = _norm(text)
        if text in {"❌ Cancelar ação", "/cancelar"} or n in {"cancelar", "cancelar acao"}:
            await app.clear_state(db, uid)
            await send_message(token, chat, "Certo. Configuração do Modo Estudo cancelada.")
            return True
        await ensure_schema(db)
        if await _active_session(db, uid):
            await app.clear_state(db, uid)
            await send_message(token, chat, "Já existe uma sessão de estudo aberta. A configuração nova foi descartada.")
            return True
        if state == "study_setup_subject":
            subject = re.sub(r"\s+", " ", text).strip(" ,.-")
            if len(subject) < 2 or len(subject) > 120:
                await send_message(token, chat, "Manda um nome/assunto entre 2 e 120 caracteres.")
                return True
            subject = await _canonical_subject(db, uid, subject)
            await app.set_state(db, uid, "study_setup_topics", {**payload, "subject": subject})
            await send_message(token, chat, f"📚 {subject}. Quais tópicos? Separe por vírgulas ou mande `sessão livre`.")
            return True
        topics = _parse_topics(text)
        if not topics:
            await send_message(token, chat, "Não consegui separar os tópicos. Ex.: `limites, derivadas, integrais`.")
            return True
        subject = payload.get("subject") or "Estudo"
        await app.clear_state(db, uid)
        session, topic = await _create_session(db, uid, subject, topics, payload)
        await send_message(token, chat, f"📚 Modo Estudo iniciado — {_row(session,'subject_name')}\n🎯 Tópico: {_row(topic,'title')}\n⏱️ {_row(session,'focus_minutes')} min de foco / {_row(session,'break_minutes')} min de pausa.\n\nO timer não conclui tópico. Você me diz quando terminou.")
        return True

    app.handle_state = handle_state_with_study
