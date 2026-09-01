"""Assistente Geral de Tempo: alertas relativos e cronômetros persistentes.

Este domínio é deliberadamente separado de ``daily_items``. Um timer rápido não
vira tarefa, compromisso nem lembrete permanente na agenda. A linguagem vem de
``temporal_language`` e a persistência usa ``quick_timers``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re

import language_primitives as language
import quality_patch
import temporal_language
from telegram_api import send_message

MIN_DELAY_SECONDS = 1
MAX_DELAY_SECONDS = 24 * 60 * 60
_SCHEMA_READY = False

_RELATIVE_TEXT_RE = re.compile(
    r"\b(?:daqui\s+a|em)\s+\d+\s*(?:segundo|segundos|seg|minuto|minutos|min|hora|horas|h)\b",
    flags=re.I,
)

_PREFIXES = (
    r"^(?:por favor\s+)?(?:me\s+)?(?:lembra|lembre|avisa|avise|recorda|recorde)\s*(?:de\s+)?",
    r"^(?:por favor\s+)?n[aã]o\s+(?:deixa|deixe)\s+(?:eu\s+)?(?:esquecer|vacilar)\s*(?:de\s+)?",
    r"^(?:por favor\s+)?(?:me\s+)?d[aá]\s+(?:um\s+)?(?:toque|aviso|al[oô])\s*(?:de\s+)?",
    r"^(?:eu\s+)?(?:tenho\s+que|tenho\s+de|preciso|devo)\s+",
)


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
    """Defesa operacional apenas quando o domínio é usado.

    A migration 0010 continua sendo a fonte formal. Este guard evita quebrar o
    primeiro pedido caso o deploy do código chegue antes da aplicação da migration.
    """
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    await db.prepare("""
        CREATE TABLE IF NOT EXISTS quick_timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('timer','quick_alert')),
            label TEXT NOT NULL,
            delay_seconds INTEGER NOT NULL CHECK(delay_seconds > 0),
            fire_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','fired','cancelled')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fired_at TEXT,
            cancelled_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_quick_timers_user_status_fire "
        "ON quick_timers(user_id,status,fire_at)"
    ).run()
    _SCHEMA_READY = True


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
    return int(_row(row, "id")) if row else None


def _now_utc():
    return datetime.now(timezone.utc)


def _parse_fire_at(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_duration(seconds):
    seconds = int(seconds)
    if seconds % 3600 == 0:
        amount = seconds // 3600
        return f"{amount} hora" if amount == 1 else f"{amount} horas"
    if seconds % 60 == 0:
        amount = seconds // 60
        return f"{amount} minuto" if amount == 1 else f"{amount} minutos"
    return f"{seconds} segundo" if seconds == 1 else f"{seconds} segundos"


def _clean_alert_label(text):
    raw = language.strip_butler(text).strip()
    raw = _RELATIVE_TEXT_RE.sub(" ", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" ,.;:-")
    for pattern in _PREFIXES:
        updated = re.sub(pattern, "", raw, flags=re.I).strip(" ,.;:-")
        if updated != raw:
            raw = updated
            break
    raw = re.sub(r"^(?:de|do|da)\s+", "", raw, flags=re.I).strip(" ,.;:-")
    return raw or "alerta rápido"


def parse_request(text):
    parsed = temporal_language.classify_quick_time_intent(text)
    kind = parsed.get("kind")
    delay = parsed.get("delay_seconds")
    if kind not in {"timer", "relative_alert"} or delay is None:
        return None
    delay = int(delay)
    if delay < MIN_DELAY_SECONDS or delay > MAX_DELAY_SECONDS:
        return {"kind": kind, "delay_seconds": delay, "invalid_range": True}
    label = "cronômetro" if kind == "timer" else _clean_alert_label(text)
    return {
        "kind": kind,
        "delay_seconds": delay,
        "label": label,
        "invalid_range": False,
    }


def _storage_kind(kind):
    """Converte a intenção linguística para o contrato persistido no D1.

    A camada de linguagem usa ``relative_alert`` porque descreve a intenção.
    O schema histórico de ``quick_timers`` usa ``quick_alert``. Manter a
    conversão num único ponto evita que novos callers voltem a violar o CHECK.
    """
    if kind == "relative_alert":
        return "quick_alert"
    if kind in {"timer", "quick_alert"}:
        return kind
    raise ValueError(f"unsupported quick timer kind: {kind}")


async def create_timer(db, uid, kind, label, delay_seconds, *, now=None):
    await ensure_schema(db)
    now = now or _now_utc()
    fire_at = now + timedelta(seconds=int(delay_seconds))
    stored_kind = _storage_kind(kind)
    result = await db.prepare(
        "INSERT INTO quick_timers(user_id,kind,label,delay_seconds,fire_at,status) "
        "VALUES(?,?,?,?,?,'active')"
    ).bind(
        int(uid), stored_kind, label, int(delay_seconds), fire_at.isoformat()
    ).run()

    timer_id = None
    meta = getattr(result, "meta", None)
    if meta is not None:
        timer_id = getattr(meta, "last_row_id", None)
        if timer_id is None:
            try:
                timer_id = meta["last_row_id"]
            except Exception:
                pass
    if timer_id is None:
        row = await db.prepare(
            "SELECT id FROM quick_timers WHERE user_id=? ORDER BY id DESC LIMIT 1"
        ).bind(int(uid)).first()
        timer_id = int(_row(row, "id")) if row else None
    return timer_id, fire_at


async def _active_timers(db, uid):
    await ensure_schema(db)
    return await _rows(
        db.prepare(
            "SELECT id,kind,label,delay_seconds,fire_at FROM quick_timers "
            "WHERE user_id=? AND status='active' ORDER BY fire_at,id"
        ).bind(int(uid))
    )


async def _cancel_timer(db, uid, timer_id):
    await ensure_schema(db)
    row = await db.prepare(
        "SELECT id,label,status FROM quick_timers WHERE id=? AND user_id=?"
    ).bind(int(timer_id), int(uid)).first()
    if not row:
        return None, "missing"
    if _row(row, "status") != "active":
        return row, "inactive"
    await db.prepare(
        "UPDATE quick_timers SET status='cancelled',cancelled_at=CURRENT_TIMESTAMP "
        "WHERE id=? AND user_id=? AND status='active'"
    ).bind(int(timer_id), int(uid)).run()
    return row, "cancelled"


def _cancel_id(text):
    normalized = language.normalize_text(language.strip_butler(text))
    match = re.fullmatch(
        r"(?:cancelar|cancela|parar|para)\s+(?:o\s+)?(?:timer|cronometro|alerta(?:\s+rapido)?)\s+#?(\d+)",
        normalized,
    )
    return int(match.group(1)) if match else None


def _is_generic_cancel(text):
    normalized = language.normalize_text(language.strip_butler(text))
    return normalized in {
        "cancelar timer", "cancela o timer", "cancela timer", "parar timer",
        "para o timer", "parar cronometro", "para o cronometro",
        "cancelar cronometro", "cancelar alerta rapido", "cancela o alerta",
    }


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None or not text:
        return False

    cancel_id = _cancel_id(text)
    cancel_request = _is_generic_cancel(text)
    request = parse_request(text)
    if request is None and not cancel_request and cancel_id is None:
        return False

    uid = await _uid(db, int(chat_id))
    if uid is None:
        return False

    if cancel_id is not None:
        row, status = await _cancel_timer(db, uid, cancel_id)
        if status == "cancelled":
            await send_message(token, int(chat_id), f"⏹️ Cancelado: {_row(row,'label')}.")
        elif status == "inactive":
            await send_message(token, int(chat_id), "⏱️ Esse timer já terminou ou já foi cancelado.")
        else:
            await send_message(token, int(chat_id), "⏱️ Não achei esse timer ativo na sua conta.")
        return True

    if cancel_request:
        active = await _active_timers(db, uid)
        if not active:
            await send_message(token, int(chat_id), "⏱️ Você não tem nenhum timer rápido ativo.")
            return True
        if len(active) == 1:
            row, _ = await _cancel_timer(db, uid, int(_row(active[0], "id")))
            await send_message(token, int(chat_id), f"⏹️ Cancelado: {_row(row,'label')}.")
            return True
        lines = ["⏱️ Tem mais de um timer ativo. Escolha pelo número:"]
        for item in active[:10]:
            lines.append(
                f"• #{int(_row(item,'id'))} — {_row(item,'label')} "
                f"({_format_duration(_row(item,'delay_seconds'))})"
            )
        lines.append("\nEx.: `cancelar timer #12`")
        await send_message(token, int(chat_id), "\n".join(lines))
        return True

    if request.get("invalid_range"):
        await send_message(
            token,
            int(chat_id),
            "⏱️ Para alerta rápido eu aceito de 1 segundo até 24 horas. "
            "Se for algo para outro dia, melhor usar um lembrete normal.",
        )
        return True

    timer_id, _ = await create_timer(
        db,
        uid,
        request["kind"],
        request["label"],
        request["delay_seconds"],
    )
    duration = _format_duration(request["delay_seconds"])
    suffix = f" (#{timer_id})" if timer_id is not None else ""
    if request["kind"] == "timer":
        response = f"⏱️ Cronômetro iniciado: {duration}{suffix}. Quando acabar eu te aviso."
    else:
        response = f"⏱️ Fechado. Em {duration} eu te aviso para {request['label']}{suffix}."
    await send_message(token, int(chat_id), response)
    return True


async def dispatch_due_quick_timers(db, token, user_id=None, *, now=None):
    """Entrega timers vencidos. ``notification_log`` + status evitam repetição."""
    now = now or _now_utc()
    sql = (
        "SELECT qt.id,qt.user_id,qt.kind,qt.label,qt.delay_seconds,qt.fire_at,u.telegram_chat_id "
        "FROM quick_timers qt JOIN users u ON u.id=qt.user_id "
        "WHERE qt.status='active' AND qt.fire_at<=?"
    )
    params = [now.isoformat()]
    if user_id is not None:
        sql += " AND qt.user_id=?"
        params.append(int(user_id))
    sql += " ORDER BY qt.fire_at,qt.id LIMIT 100"
    try:
        due = await _rows(db.prepare(sql).bind(*params))
    except Exception:
        # Código pode chegar antes da migration; sem timer criado ainda, não há
        # trabalho útil a fazer e o próximo pedido do domínio aplica o guard.
        return

    for item in due:
        timer_id = int(_row(item, "id"))
        uid = int(_row(item, "user_id"))
        key = f"quick_timer:{timer_id}"
        sent = await db.prepare(
            "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
        ).bind(uid, key).first()
        if sent:
            await db.prepare(
                "UPDATE quick_timers SET status='fired',fired_at=COALESCE(fired_at,CURRENT_TIMESTAMP) "
                "WHERE id=? AND user_id=? AND status='active'"
            ).bind(timer_id, uid).run()
            continue

        kind = _row(item, "kind")
        label = _row(item, "label")
        if kind == "timer":
            text = f"⏰ Tempo! {_format_duration(_row(item,'delay_seconds'))} encerrados."
        else:
            text = f"⏰ Hora de {label}."

        # scheduled_delivery_guard instala confirmação real neste sender.
        await quality_patch.send_message(token, int(_row(item, "telegram_chat_id")), text)
        await db.prepare(
            "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
        ).bind(uid, key).run()
        await db.prepare(
            "UPDATE quick_timers SET status='fired',fired_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND user_id=? AND status='active'"
        ).bind(timer_id, uid).run()


async def next_quick_timer(db, uid, *, now=None):
    """Retorna o próximo instante armável do usuário para ``PersonalAlarm``."""
    now = now or _now_utc()
    try:
        row = await db.prepare(
            "SELECT fire_at FROM quick_timers WHERE user_id=? AND status='active' "
            "ORDER BY fire_at,id LIMIT 1"
        ).bind(int(uid)).first()
    except Exception:
        return None
    fire_at = _parse_fire_at(_row(row, "fire_at")) if row else None
    if fire_at is None:
        return None
    if fire_at <= now:
        return now + timedelta(seconds=1)
    return fire_at
