"""Otimizações do caminho quente do Worker.

A regra aqui é simples: durante um único update do Telegram, ``telegram_chat_id``
e ``user_sessions`` são dados estáveis até que o próprio Butler os altere. Vários
handlers antigos resolviam os mesmos dados de forma independente, multiplicando
round-trips ao D1 antes da resposta.

O cache é reiniciado no começo do dispatcher interativo e atualizado sempre que
um estado é escrito. Não existe cache persistente entre updates.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy

import app
import academic_import


_REQUEST_CACHE = ContextVar("butler_request_cache", default=None)
_INSTALLED = False

_original_ensure_user = app.ensure_user
_original_get_state = app.get_state
_original_set_state = app.set_state


def reset_request_cache():
    """Inicia um cache vazio para o update atual do Telegram."""
    _REQUEST_CACHE.set({"uids": {}, "states": {}})


def _cache():
    cache = _REQUEST_CACHE.get()
    if cache is None:
        cache = {"uids": {}, "states": {}}
        _REQUEST_CACHE.set(cache)
    return cache


def _remember_uid(chat_id, uid):
    _cache()["uids"][int(chat_id)] = uid


def _remember_state(uid, state, payload):
    _cache()["states"][int(uid)] = (state, deepcopy(payload or {}))


async def cached_uid(db, chat_id):
    """Resolve ``telegram_chat_id -> users.id`` no máximo uma vez por update."""
    chat_id = int(chat_id)
    cache = _cache()["uids"]
    if chat_id in cache:
        return cache[chat_id]

    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    uid = int(app.rowget(row, "id")) if row else None
    cache[chat_id] = uid
    return uid


async def cached_get_state(db, user_id):
    """Reaproveita ``user_sessions`` entre handlers do mesmo update."""
    user_id = int(user_id)
    states = _cache()["states"]
    if user_id in states:
        state, payload = states[user_id]
        return state, deepcopy(payload)

    state, payload = await _original_get_state(db, user_id)
    _remember_state(user_id, state, payload)
    return state, deepcopy(payload)


async def cached_set_state(db, user_id, state=None, payload=None):
    await _original_set_state(db, user_id, state, payload)
    _remember_state(user_id, state, payload or {})


async def cached_clear_state(db, user_id):
    await cached_set_state(db, user_id, None, {})


async def fast_ensure_user(db, chat_id, user):
    """Evita repetir o bootstrap completo para usuários já conhecidos."""
    existing = await db.prepare(
        "SELECT id,preferred_name,is_owner FROM users WHERE telegram_chat_id=?"
    ).bind(chat_id).first()

    if existing:
        uid = int(app.rowget(existing, "id"))
        preferred = app.rowget(existing, "preferred_name")
        _remember_uid(chat_id, uid)
        return uid, False, preferred

    result = await _original_ensure_user(db, chat_id, user)
    try:
        _remember_uid(chat_id, int(result[0]))
    except Exception:
        pass
    return result


def _patch_uid_helpers():
    """Aponta helpers equivalentes para a resolução compartilhada.

    A lista é explícita para não substituir funções chamadas ``_uid`` que possam
    ter contrato diferente em módulos futuros.
    """
    import colloquial_reminder_fastpath
    import conversation_layer
    import correction_patch
    import goal_operational
    import natural_behavior_patch
    import operational_informal_fastpath
    import operational_menu
    import production_usability_patch
    import quality_patch
    import reference_patch
    import runtime_guard
    import task_context_patch
    import weather_context

    for module, attr in (
        (runtime_guard, "_uid"),
        (goal_operational, "_uid"),
        (operational_menu, "_uid"),
        (quality_patch, "_uid"),
        (weather_context, "_uid"),
        (reference_patch, "_uid"),
        (correction_patch, "_uid"),
        (task_context_patch, "_uid"),
        (natural_behavior_patch, "_uid"),
        (conversation_layer, "_uid"),
        (colloquial_reminder_fastpath, "_uid"),
        (operational_informal_fastpath, "_uid"),
        (production_usability_patch, "_resolve_user"),
    ):
        if hasattr(module, attr):
            setattr(module, attr, cached_uid)


def _patch_runtime_state_helpers():
    import runtime_guard

    original_runtime_set = runtime_guard._set_state

    async def runtime_state(db, uid):
        return await cached_get_state(db, uid)

    async def runtime_set_state(db, uid, state, payload=""):
        normalized = payload if isinstance(payload, dict) else {"value": payload}
        await original_runtime_set(db, uid, state, payload)
        _remember_state(uid, state, normalized)

    async def runtime_clear(db, uid):
        await runtime_set_state(db, uid, None, {})

    runtime_guard._state = runtime_state
    runtime_guard._set_state = runtime_set_state
    runtime_guard._clear = runtime_clear


def install_performance_patches():
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    app.ensure_user = fast_ensure_user
    app.get_state = cached_get_state
    app.set_state = cached_set_state
    app.clear_state = cached_clear_state

    _patch_runtime_state_helpers()
    _patch_uid_helpers()

    # ``entry.py`` ainda usa uma cadeia explícita de installers. O importador é
    # um módulo acadêmico próprio; este hook apenas garante que ele entre cedo no
    # bootstrap para que ``academic_polish`` possa encadear o wrapper de estado.
    academic_import.install()
