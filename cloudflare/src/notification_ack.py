"""Respostas sociais opcionais a avisos efêmeros recentes.

Um timer, alerta rápido ou lembrete simples já terminou quando o Butler avisa.
Responder ``valeu``, ``desliguei`` ou ``já foi`` não é obrigatório e não altera
agenda; serve apenas para a conversa não terminar de forma seca.

Tarefas/compromissos ficam fora deste módulo: neles ``feito`` deve continuar
mudando o estado persistente da obrigação.

Regra de segurança: esta camada é best-effort. Se o contexto social falhar, a
entrega do alerta nunca pode falhar junto com ele.
"""
from __future__ import annotations

import json

import language_primitives as language
import runtime_guard
from telegram_api import send_message

ACK_WINDOW_MINUTES = 10

_GRATITUDE = {
    "valeu", "obrigado", "obrigada", "obg", "vlw", "tmj", "tamo junto",
    "fechou", "fechado", "beleza", "tranquilo", "certo", "boa",
}
_DONE = {
    "desliguei", "ja foi", "feito", "resolvido", "resolvida", "terminei",
    "pronto", "concluido", "concluida", "deu certo", "foi", "ja fiz",
}
_ALLOWED_DOMAINS = {"quick_alert", "timer", "simple_reminder"}


def _norm(text):
    return language.normalize_text(language.strip_butler(text))


def ack_kind(text):
    n = _norm(text)
    if n in _GRATITUDE:
        return "thanks"
    if n in _DONE:
        return "done"
    return None


async def remember_notification(db, uid, domain, target_id, label):
    """Registra contexto curto sem nunca comprometer a entrega principal."""
    if domain not in _ALLOWED_DOMAINS:
        return False
    detail = json.dumps(
        {"domain": domain, "label": str(label or "")[:160]},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    try:
        await db.prepare(
            "INSERT INTO natural_events(user_id,event_type,target_id,detail) "
            "VALUES(?,'notification_sent',?,?)"
        ).bind(int(uid), int(target_id) if target_id is not None else None, detail).run()
        return True
    except Exception as exc:
        print(
            f"[notification-ack] remember-failed type={type(exc).__name__} "
            f"message={str(exc)[:240]}"
        )
        return False


async def _recent_unacked(db, uid):
    try:
        return await db.prepare(
            "SELECT n.id,n.target_id,n.detail,n.created_at "
            "FROM natural_events n "
            "WHERE n.user_id=? AND n.event_type='notification_sent' "
            "AND datetime(n.created_at) >= datetime('now', ?) "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM natural_events a "
            "  WHERE a.user_id=n.user_id AND a.event_type='notification_ack' "
            "    AND a.target_id=n.id"
            ") "
            "ORDER BY n.id DESC LIMIT 1"
        ).bind(int(uid), f"-{ACK_WINDOW_MINUTES} minutes").first()
    except Exception:
        return None


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


def _response(kind, event_id):
    if kind == "done":
        variants = ("Boa, então tá resolvido. 👌", "Fechado. ✅", "Perfeito, chefe. 👌")
    else:
        variants = ("Tamo junto. 👌", "Disponha, chefe.", "Fechado. 👍")
    return variants[int(event_id or 0) % len(variants)]


async def handle_message(db, token, message):
    text = (message.get("text") or "").strip()
    kind = ack_kind(text)
    if kind is None:
        # Gate lexical: conversa comum não toca D1 por causa deste recurso.
        return False

    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    uid = await runtime_guard._uid(db, int(chat_id))
    if uid is None:
        return False

    event = await _recent_unacked(db, uid)
    if not event:
        return False

    event_id = int(_row(event, "id"))
    try:
        await db.prepare(
            "INSERT INTO natural_events(user_id,event_type,target_id,detail) "
            "VALUES(?,'notification_ack',?,?)"
        ).bind(int(uid), event_id, kind).run()
    except Exception:
        return False
    await send_message(token, int(chat_id), _response(kind, event_id))
    return True
