"""Contexto operacional curto para referências da Etapa 1.3.

Este módulo centraliza somente contexto recente de entidades operacionais. Ele não
executa CRUD de domínio e não envia Telegram. A autoridade de escrita continua
nos módulos de tarefa/compromisso/lembrete.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

import language_primitives as language
from nlu import parse_date
from settings import UTC_OFFSET_HOURS

CONTEXT_MAX_AGE_MINUTES = 30
LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))


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


def _parse_sqlite_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except Exception:
        try:
            parsed = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def context_is_fresh(created_at: str | None, *, now: datetime | None = None, max_age_minutes: int = CONTEXT_MAX_AGE_MINUTES) -> bool:
    """Retorna se um contexto ainda pode sustentar pronomes/referências curtas."""
    created = _parse_sqlite_timestamp(created_at)
    if created is None:
        return False
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_seconds = (current - created).total_seconds()
    return 0 <= age_seconds <= max_age_minutes * 60


def ordinal_index(text: str | None) -> int | None:
    normalized = language.normalize_text(language.strip_butler(text))
    mapping = {
        "primeira": 0,
        "primeiro": 0,
        "segunda": 1,
        "segundo": 1,
        "terceira": 2,
        "terceiro": 2,
    }
    for word, index in mapping.items():
        if f" {word} " in f" {normalized} ":
            return index
    return None


def should_consume_context(text: str | None) -> bool:
    """Contexto antigo nunca vence uma mensagem nova por simples coincidência.

    Só abrimos a porta do contexto quando há uma referência explícita, uma
    posição ordinal clara ou um follow-up curtíssimo já conhecido. Ações novas
    de criação são barreira.
    """
    normalized = language.normalize_text(language.strip_butler(text))
    if not normalized:
        return False

    families = set(language.detect_action_families(text))
    if families.intersection(
        {
            "reminder",
            "create_task",
            "create_appointment",
            "scheduled_event",
            "create_routine",
            "planned_activity",
            "timer",
        }
    ):
        return False

    if language.detect_references(text) or ordinal_index(text) is not None:
        return True

    return normalized in {
        "certo",
        "ok",
        "feito",
        "pronto",
        "ja foi",
        "adiar",
        "adia",
        "depois",
        "mais tarde",
        "agora nao",
        "nao agora",
        "daqui a pouco",
        "mantem",
        "pendente",
    }


def referenced_candidate_id(payload: dict | None, text: str | None) -> int | None:
    """Resolve referência puramente a partir do payload recente, quando seguro."""
    payload = payload or {}
    candidates = [int(x) for x in (payload.get("candidate_ids") or []) if str(x).isdigit()]

    idx = ordinal_index(text)
    if idx is not None:
        return candidates[idx] if idx < len(candidates) else None

    refs = language.detect_references(text)
    if not refs:
        return payload.get("id") if should_consume_context(text) else None

    kinds = {ref.get("kind") for ref in refs}
    values = {ref.get("value") for ref in refs}

    if values.intersection({"a ultima", "o ultimo"}):
        try:
            return int(payload.get("id"))
        except Exception:
            return None

    if "alternative" in kinds:
        current = payload.get("id")
        alternatives = [item_id for item_id in candidates if item_id != current]
        return alternatives[0] if len(alternatives) == 1 else None

    if "previous" in kinds:
        history = [int(x) for x in (payload.get("history_ids") or []) if str(x).isdigit()]
        return history[1] if len(history) > 1 else None

    if (
        "latest" in kinds
        or kinds.intersection({"deictic", "pronoun"})
        or values.intersection({"aquela", "aquele"})
    ):
        try:
            return int(payload.get("id"))
        except Exception:
            return None

    return None


def reference_due_date_qualifier(text: str | None, *, today=None):
    """Extrai data apenas quando ela qualifica a referência, não a nova ação.

    `muda ela pra sexta` usa sexta como destino e não como filtro do item atual.
    Já `cancela aquela de amanhã` exige que o alvo atual seja realmente de amanhã.
    """
    if "reschedule" in set(language.detect_action_families(text)):
        return None
    normalized = language.normalize_text(language.strip_butler(text), keep_temporal=True)
    match = re.search(
        r"\b(?:essa|esse|aquela|aquele|a ultima|o ultimo|a anterior|o anterior)\s+(?:de|da|do)\s+"
        r"(hoje|amanha|segunda|terca|quarta|quinta|sexta|sabado|domingo)\b",
        normalized,
    )
    if not match:
        return None
    base = today or datetime.now(timezone.utc).astimezone(LOCAL_TZ).date()
    return parse_date(match.group(1), base)


async def remember(
    db,
    uid: int,
    kind: str,
    target_id: int | None = None,
    detail: dict | None = None,
    *,
    candidate_ids: list[int] | None = None,
):
    """Grava contexto por usuário mantendo histórico e lista ativa quando seguro.

    Se um turno muda o foco para um item que já pertence à lista recém-exibida ou
    recém-criada, preservamos ``candidate_ids``. Isso permite sequências como
    `conclui a primeira` -> `cancela a segunda`. Um item novo fora daquela lista
    nunca herda candidatos antigos.
    """
    history_ids: list[int] = []
    previous = await latest(db, uid, allow_stale=False)

    effective_candidates = [int(x) for x in (candidate_ids or [])]
    if candidate_ids is None and previous and target_id is not None:
        previous_candidates = []
        for value in previous.get("candidate_ids") or []:
            try:
                previous_candidates.append(int(value))
            except Exception:
                continue
        try:
            current_target = int(target_id)
        except Exception:
            current_target = None
        if current_target is not None and current_target in previous_candidates:
            effective_candidates = previous_candidates

    if previous:
        for value in [previous.get("id"), *(previous.get("history_ids") or [])]:
            try:
                item_id = int(value)
            except Exception:
                continue
            if item_id not in history_ids and item_id != target_id:
                history_ids.append(item_id)
            if len(history_ids) >= 4:
                break

    payload = {
        "kind": kind,
        "domain": kind,
        "id": target_id,
        "detail": detail or {},
        "candidate_ids": effective_candidates,
        "history_ids": ([int(target_id)] if target_id is not None else []) + history_ids,
        "context_version": 2,
    }
    await db.prepare(
        "INSERT INTO natural_events(user_id,event_type,target_id,detail) VALUES(?,'context',?,?)"
    ).bind(uid, target_id, json.dumps(payload, ensure_ascii=False)).run()
    return payload


async def remember_list(
    db,
    uid: int,
    kind: str,
    candidate_ids: list[int],
    *,
    source: str = "list",
):
    ids = [int(x) for x in candidate_ids]
    target = ids[0] if ids else None
    return await remember(db, uid, kind, target, {"source": source}, candidate_ids=ids)


async def latest(db, uid: int, *, allow_stale: bool = False) -> dict | None:
    row = await db.prepare(
        "SELECT detail,created_at FROM natural_events WHERE user_id=? AND event_type='context' ORDER BY id DESC LIMIT 1"
    ).bind(uid).first()
    if not row:
        return None
    created_at = _row(row, "created_at")
    if not allow_stale and not context_is_fresh(created_at):
        return None
    try:
        payload = json.loads(_row(row, "detail") or "{}")
    except Exception:
        return None
    payload["_created_at"] = created_at
    return payload


async def resolve_daily_item(db, uid: int, text: str | None, *, kind: str | None = None):
    """Resolve somente um alvo inequívoco de `daily_items` a partir do contexto."""
    if not should_consume_context(text):
        return None
    payload = await latest(db, uid)
    if not payload:
        return None
    if kind and payload.get("kind") != kind:
        return None
    target_id = referenced_candidate_id(payload, text)
    if target_id is None:
        return None
    sql = "SELECT * FROM daily_items WHERE id=? AND user_id=?"
    params = [target_id, uid]
    if kind:
        sql += " AND kind=?"
        params.append(kind)
    row = await db.prepare(sql).bind(*params).first()
    if not row:
        return None

    qualifier = reference_due_date_qualifier(text)
    if qualifier is not None and _row(row, "due_date") != qualifier.isoformat():
        return None
    return row


# Compatibilidade para módulos antigos que ainda chamam conversation_layer._remember
# e conversation_layer._context. A Etapa 1.3 não cria uma segunda fonte de contexto:
# ambos passam a delegar para esta autoridade e herdam expiração/histórico.
async def legacy_remember(db, uid, kind, target_id=None, detail=None):
    return await remember(db, uid, kind, target_id, detail)


async def legacy_context(db, uid):
    return await latest(db, uid)


def install():
    """Redireciona a API de contexto legada para a autoridade da Etapa 1.3."""
    import conversation_layer

    conversation_layer._remember = legacy_remember
    conversation_layer._context = legacy_context
