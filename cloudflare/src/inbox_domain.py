"""Autoridade de persistência da Etapa 5 — Caixa de entrada.

A Inbox serve para captura sem classificação imediata. Conversão para outros
domínios só acontece depois de escolha explícita do usuário.
"""
from __future__ import annotations

import re

VALID_STATUSES = {"pending", "converted", "archived"}
VALID_SOURCES = {"text", "button"}


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


def normalize_content(content):
    value = re.sub(r"\s+", " ", str(content or "").strip())
    if not value:
        raise ValueError("conteúdo vazio")
    if len(value) > 1000:
        raise ValueError("conteúdo acima de 1000 caracteres")
    return value


async def capture(db, user_id, content, *, source="text"):
    content = normalize_content(content)
    if source not in VALID_SOURCES:
        raise ValueError("fonte inválida")
    result = await db.prepare(
        "INSERT INTO inbox_items(user_id,content,source,status) VALUES(?,?,?,'pending')"
    ).bind(int(user_id), content, source).run()
    item_id = getattr(result, "last_row_id", None)
    if item_id is None:
        meta = getattr(result, "meta", None)
        item_id = getattr(meta, "last_row_id", None)
    if item_id is None:
        row = await db.prepare(
            "SELECT id FROM inbox_items WHERE user_id=? ORDER BY id DESC LIMIT 1"
        ).bind(int(user_id)).first()
        item_id = _row(row, "id")
    return int(item_id)


async def list_items(db, user_id, *, status="pending", limit=30):
    if status not in VALID_STATUSES:
        raise ValueError("status inválido")
    limit = max(1, min(int(limit), 50))
    return await _rows(
        db.prepare(
            f"SELECT id,content,source,status,converted_domain,converted_target_id,created_at,updated_at "
            f"FROM inbox_items WHERE user_id=? AND status=? "
            f"ORDER BY created_at ASC,id ASC LIMIT {limit}"
        ).bind(int(user_id), status)
    )


async def get_item(db, user_id, item_id):
    return await db.prepare(
        "SELECT id,user_id,content,source,status,converted_domain,converted_target_id,created_at,updated_at "
        "FROM inbox_items WHERE id=? AND user_id=? LIMIT 1"
    ).bind(int(item_id), int(user_id)).first()


async def archive(db, user_id, item_id):
    item = await get_item(db, user_id, item_id)
    if not item:
        raise LookupError("item não encontrado")
    if _row(item, "status") == "converted":
        raise ValueError("item convertido não pode ser arquivado como pendente")
    await db.prepare(
        "UPDATE inbox_items SET status='archived',archived_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP "
        "WHERE id=? AND user_id=?"
    ).bind(int(item_id), int(user_id)).run()
    return True


async def reopen(db, user_id, item_id):
    item = await get_item(db, user_id, item_id)
    if not item:
        raise LookupError("item não encontrado")
    if _row(item, "status") != "archived":
        raise ValueError("somente item arquivado pode ser reaberto")
    await db.prepare(
        "UPDATE inbox_items SET status='pending',archived_at=NULL,updated_at=CURRENT_TIMESTAMP "
        "WHERE id=? AND user_id=?"
    ).bind(int(item_id), int(user_id)).run()
    return True


async def mark_converted(db, user_id, item_id, domain, target_id):
    item = await get_item(db, user_id, item_id)
    if not item:
        raise LookupError("item não encontrado")
    if _row(item, "status") == "archived":
        raise ValueError("item arquivado precisa ser reaberto antes da conversão")
    if _row(item, "status") == "converted":
        same = (
            str(_row(item, "converted_domain")) == str(domain)
            and int(_row(item, "converted_target_id")) == int(target_id)
        )
        if same:
            return True
        raise ValueError("item já convertido")
    await db.prepare(
        "UPDATE inbox_items SET status='converted',converted_domain=?,converted_target_id=?,"
        "converted_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP "
        "WHERE id=? AND user_id=? AND status='pending'"
    ).bind(str(domain), int(target_id), int(item_id), int(user_id)).run()
    return True
