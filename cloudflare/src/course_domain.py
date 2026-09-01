"""Domínio autoritativo de Cursos e Trilhas — Etapa 4.1.

Este módulo não conversa com Telegram e não decide linguagem natural. Ele expõe
operações determinísticas sobre o modelo de cursos. Progresso só muda por chamada
explícita: ordenar conteúdos, passar o tempo ou iniciar Modo Estudo nunca conclui
uma aula automaticamente.

A migration ``0013_courses.sql`` é a fonte formal do schema.
"""
from __future__ import annotations

import json

COURSE_MODES = {"self_paced", "live"}
COURSE_STATUSES = {"active", "paused", "completed", "archived"}
CONTENT_KINDS = {"lesson", "reading", "exercise", "project", "review", "other"}
CONTENT_STATUSES = {"pending", "completed", "skipped"}
MATERIAL_KINDS = {"link", "file", "video", "text", "other"}
ACTIVITY_STATUSES = {"pending", "completed", "skipped"}


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


def _clean_title(value, *, max_len=180):
    title = " ".join(str(value or "").split()).strip()
    if not title:
        raise ValueError("title is required")
    if len(title) > max_len:
        raise ValueError(f"title exceeds {max_len} characters")
    return title


def _clean_optional(value, *, max_len=2000):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def _last_row_id(result):
    meta = getattr(result, "meta", None)
    if meta is not None:
        value = getattr(meta, "last_row_id", None)
        if value is None:
            try:
                value = meta["last_row_id"]
            except Exception:
                value = None
        if value is not None:
            return int(value)
    value = getattr(result, "last_row_id", None)
    return int(value) if value is not None else None


async def _owned_course(db, user_id, course_id):
    return await db.prepare(
        "SELECT id,user_id,title,mode,status,description,created_at,updated_at,completed_at "
        "FROM courses WHERE id=? AND user_id=?"
    ).bind(int(course_id), int(user_id)).first()


async def _owned_module(db, user_id, course_id, module_id):
    return await db.prepare(
        "SELECT m.id,m.course_id,m.position,m.title,m.description "
        "FROM course_modules m JOIN courses c ON c.id=m.course_id "
        "WHERE m.id=? AND m.course_id=? AND c.user_id=?"
    ).bind(int(module_id), int(course_id), int(user_id)).first()


async def _owned_content(db, user_id, course_id, content_id):
    return await db.prepare(
        "SELECT ct.id,ct.module_id,ct.position,ct.title,ct.kind,ct.status,ct.scheduled_at,ct.notes "
        "FROM course_contents ct "
        "JOIN course_modules m ON m.id=ct.module_id "
        "JOIN courses c ON c.id=m.course_id "
        "WHERE ct.id=? AND c.id=? AND c.user_id=?"
    ).bind(int(content_id), int(course_id), int(user_id)).first()


async def _next_position(db, table, parent_column, parent_id):
    allowed = {
        "course_modules": "course_id",
        "course_contents": "module_id",
        "course_materials": "content_id",
        "course_activities": "content_id",
    }
    if allowed.get(table) != parent_column:
        raise ValueError("invalid position target")
    row = await db.prepare(
        f"SELECT COALESCE(MAX(position),0)+1 AS next_position FROM {table} WHERE {parent_column}=?"
    ).bind(int(parent_id)).first()
    return int(_row(row, "next_position", 1) or 1)


async def _event(db, course_id, event_type, *, module_id=None, content_id=None, activity_id=None, detail=None):
    payload = None
    if detail is not None:
        payload = json.dumps(detail, ensure_ascii=False, separators=(",", ":")) if not isinstance(detail, str) else detail
    await db.prepare(
        "INSERT INTO course_events(course_id,module_id,content_id,activity_id,event_type,detail) "
        "VALUES(?,?,?,?,?,?)"
    ).bind(
        int(course_id),
        int(module_id) if module_id is not None else None,
        int(content_id) if content_id is not None else None,
        int(activity_id) if activity_id is not None else None,
        str(event_type),
        payload,
    ).run()


async def create_course(db, user_id, title, *, mode="self_paced", description=None):
    mode = str(mode or "").strip()
    if mode not in COURSE_MODES:
        raise ValueError("invalid course mode")
    title = _clean_title(title)
    result = await db.prepare(
        "INSERT INTO courses(user_id,title,mode,description) VALUES(?,?,?,?)"
    ).bind(int(user_id), title, mode, _clean_optional(description)).run()
    course_id = _last_row_id(result)
    if course_id is None:
        row = await db.prepare(
            "SELECT id FROM courses WHERE user_id=? ORDER BY id DESC LIMIT 1"
        ).bind(int(user_id)).first()
        course_id = int(_row(row, "id")) if row else None
    if course_id is None:
        raise RuntimeError("course insert did not return an id")
    await _event(db, course_id, "course_created", detail={"mode": mode})
    return course_id


async def add_module(db, user_id, course_id, title, *, description=None, position=None):
    if not await _owned_course(db, user_id, course_id):
        raise LookupError("course not found")
    title = _clean_title(title)
    if position is None:
        position = await _next_position(db, "course_modules", "course_id", course_id)
    if int(position) < 1:
        raise ValueError("position must be positive")
    result = await db.prepare(
        "INSERT INTO course_modules(course_id,position,title,description) VALUES(?,?,?,?)"
    ).bind(int(course_id), int(position), title, _clean_optional(description)).run()
    module_id = _last_row_id(result)
    if module_id is None:
        row = await db.prepare(
            "SELECT id FROM course_modules WHERE course_id=? AND position=?"
        ).bind(int(course_id), int(position)).first()
        module_id = int(_row(row, "id")) if row else None
    await _event(db, course_id, "module_added", module_id=module_id, detail={"position": int(position)})
    return module_id


async def add_content(
    db,
    user_id,
    course_id,
    module_id,
    title,
    *,
    kind="lesson",
    position=None,
    scheduled_at=None,
    notes=None,
):
    if not await _owned_module(db, user_id, course_id, module_id):
        raise LookupError("module not found")
    kind = str(kind or "").strip()
    if kind not in CONTENT_KINDS:
        raise ValueError("invalid content kind")
    title = _clean_title(title)
    if position is None:
        position = await _next_position(db, "course_contents", "module_id", module_id)
    if int(position) < 1:
        raise ValueError("position must be positive")
    result = await db.prepare(
        "INSERT INTO course_contents(module_id,position,title,kind,scheduled_at,notes) "
        "VALUES(?,?,?,?,?,?)"
    ).bind(
        int(module_id), int(position), title, kind,
        _clean_optional(scheduled_at, max_len=80), _clean_optional(notes),
    ).run()
    content_id = _last_row_id(result)
    if content_id is None:
        row = await db.prepare(
            "SELECT id FROM course_contents WHERE module_id=? AND position=?"
        ).bind(int(module_id), int(position)).first()
        content_id = int(_row(row, "id")) if row else None
    await _event(
        db, course_id, "content_added", module_id=module_id, content_id=content_id,
        detail={"position": int(position), "kind": kind},
    )
    return content_id


async def add_material(db, user_id, course_id, content_id, title, *, kind="other", reference=None, position=None):
    content = await _owned_content(db, user_id, course_id, content_id)
    if not content:
        raise LookupError("content not found")
    kind = str(kind or "").strip()
    if kind not in MATERIAL_KINDS:
        raise ValueError("invalid material kind")
    title = _clean_title(title)
    if position is None:
        position = await _next_position(db, "course_materials", "content_id", content_id)
    result = await db.prepare(
        "INSERT INTO course_materials(content_id,position,title,kind,reference) VALUES(?,?,?,?,?)"
    ).bind(int(content_id), int(position), title, kind, _clean_optional(reference, max_len=4000)).run()
    material_id = _last_row_id(result)
    if material_id is None:
        row = await db.prepare(
            "SELECT id FROM course_materials WHERE content_id=? AND position=?"
        ).bind(int(content_id), int(position)).first()
        material_id = int(_row(row, "id")) if row else None
    await _event(db, course_id, "material_added", module_id=_row(content, "module_id"), content_id=content_id, detail={"kind": kind})
    return material_id


async def add_activity(db, user_id, course_id, content_id, title, *, notes=None, position=None):
    content = await _owned_content(db, user_id, course_id, content_id)
    if not content:
        raise LookupError("content not found")
    title = _clean_title(title)
    if position is None:
        position = await _next_position(db, "course_activities", "content_id", content_id)
    result = await db.prepare(
        "INSERT INTO course_activities(content_id,position,title,notes) VALUES(?,?,?,?)"
    ).bind(int(content_id), int(position), title, _clean_optional(notes)).run()
    activity_id = _last_row_id(result)
    if activity_id is None:
        row = await db.prepare(
            "SELECT id FROM course_activities WHERE content_id=? AND position=?"
        ).bind(int(content_id), int(position)).first()
        activity_id = int(_row(row, "id")) if row else None
    await _event(db, course_id, "activity_added", module_id=_row(content, "module_id"), content_id=content_id, activity_id=activity_id)
    return activity_id


async def set_content_status(db, user_id, course_id, content_id, status):
    """Muda progresso somente por chamada explícita do domínio."""
    status = str(status or "").strip()
    if status not in CONTENT_STATUSES:
        raise ValueError("invalid content status")
    content = await _owned_content(db, user_id, course_id, content_id)
    if not content:
        raise LookupError("content not found")
    await db.prepare(
        "UPDATE course_contents SET status=?, "
        "completed_at=CASE WHEN ?='completed' THEN CURRENT_TIMESTAMP ELSE NULL END, "
        "skipped_at=CASE WHEN ?='skipped' THEN CURRENT_TIMESTAMP ELSE NULL END, "
        "updated_at=CURRENT_TIMESTAMP WHERE id=?"
    ).bind(status, status, status, int(content_id)).run()
    await _event(
        db, course_id, f"content_{status}", module_id=_row(content, "module_id"),
        content_id=content_id,
    )
    return True


async def set_activity_status(db, user_id, course_id, activity_id, status):
    status = str(status or "").strip()
    if status not in ACTIVITY_STATUSES:
        raise ValueError("invalid activity status")
    row = await db.prepare(
        "SELECT a.id,a.content_id,ct.module_id FROM course_activities a "
        "JOIN course_contents ct ON ct.id=a.content_id "
        "JOIN course_modules m ON m.id=ct.module_id "
        "JOIN courses c ON c.id=m.course_id "
        "WHERE a.id=? AND c.id=? AND c.user_id=?"
    ).bind(int(activity_id), int(course_id), int(user_id)).first()
    if not row:
        raise LookupError("activity not found")
    await db.prepare(
        "UPDATE course_activities SET status=?, "
        "completed_at=CASE WHEN ?='completed' THEN CURRENT_TIMESTAMP ELSE NULL END, "
        "skipped_at=CASE WHEN ?='skipped' THEN CURRENT_TIMESTAMP ELSE NULL END, "
        "updated_at=CURRENT_TIMESTAMP WHERE id=?"
    ).bind(status, status, status, int(activity_id)).run()
    await _event(
        db, course_id, f"activity_{status}", module_id=_row(row, "module_id"),
        content_id=_row(row, "content_id"), activity_id=activity_id,
    )
    return True


async def set_course_status(db, user_id, course_id, status):
    """Conclusão do curso também é explícita; não é inferida dos conteúdos."""
    status = str(status or "").strip()
    if status not in COURSE_STATUSES:
        raise ValueError("invalid course status")
    if not await _owned_course(db, user_id, course_id):
        raise LookupError("course not found")
    await db.prepare(
        "UPDATE courses SET status=?, "
        "completed_at=CASE WHEN ?='completed' THEN CURRENT_TIMESTAMP ELSE NULL END, "
        "updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?"
    ).bind(status, status, int(course_id), int(user_id)).run()
    await _event(db, course_id, f"course_{status}")
    return True


async def next_content(db, user_id, course_id):
    """Retorna o próximo conteúdo pendente sem alterar qualquer progresso."""
    course = await _owned_course(db, user_id, course_id)
    if not course:
        raise LookupError("course not found")
    mode = _row(course, "mode")
    if mode == "live":
        order = "CASE WHEN ct.scheduled_at IS NULL THEN 1 ELSE 0 END, ct.scheduled_at, m.position, ct.position"
    else:
        order = "m.position, ct.position"
    return await db.prepare(
        "SELECT ct.id,ct.module_id,m.title AS module_title,m.position AS module_position,"
        "ct.position,ct.title,ct.kind,ct.status,ct.scheduled_at "
        "FROM course_contents ct JOIN course_modules m ON m.id=ct.module_id "
        "JOIN courses c ON c.id=m.course_id "
        "WHERE c.id=? AND c.user_id=? AND ct.status='pending' "
        f"ORDER BY {order} LIMIT 1"
    ).bind(int(course_id), int(user_id)).first()


async def progress_summary(db, user_id, course_id):
    if not await _owned_course(db, user_id, course_id):
        raise LookupError("course not found")
    row = await db.prepare(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN ct.status='completed' THEN 1 ELSE 0 END) AS completed, "
        "SUM(CASE WHEN ct.status='skipped' THEN 1 ELSE 0 END) AS skipped, "
        "SUM(CASE WHEN ct.status='pending' THEN 1 ELSE 0 END) AS pending "
        "FROM course_contents ct JOIN course_modules m ON m.id=ct.module_id "
        "WHERE m.course_id=?"
    ).bind(int(course_id)).first()
    total = int(_row(row, "total", 0) or 0)
    completed = int(_row(row, "completed", 0) or 0)
    skipped = int(_row(row, "skipped", 0) or 0)
    pending = int(_row(row, "pending", 0) or 0)
    return {
        "total": total,
        "completed": completed,
        "skipped": skipped,
        "pending": pending,
        "percent_completed": round((completed / total) * 100, 1) if total else 0.0,
        "percent_resolved": round(((completed + skipped) / total) * 100, 1) if total else 0.0,
    }


async def course_structure(db, user_id, course_id):
    course = await _owned_course(db, user_id, course_id)
    if not course:
        raise LookupError("course not found")
    modules = await _rows(
        db.prepare(
            "SELECT id,position,title,description FROM course_modules "
            "WHERE course_id=? ORDER BY position,id"
        ).bind(int(course_id))
    )
    result = {
        "id": int(_row(course, "id")),
        "title": _row(course, "title"),
        "mode": _row(course, "mode"),
        "status": _row(course, "status"),
        "description": _row(course, "description"),
        "modules": [],
    }
    for module in modules:
        module_id = int(_row(module, "id"))
        contents = await _rows(
            db.prepare(
                "SELECT id,position,title,kind,status,scheduled_at,notes FROM course_contents "
                "WHERE module_id=? ORDER BY position,id"
            ).bind(module_id)
        )
        result["modules"].append({
            "id": module_id,
            "position": int(_row(module, "position")),
            "title": _row(module, "title"),
            "description": _row(module, "description"),
            "contents": [
                {
                    "id": int(_row(item, "id")),
                    "position": int(_row(item, "position")),
                    "title": _row(item, "title"),
                    "kind": _row(item, "kind"),
                    "status": _row(item, "status"),
                    "scheduled_at": _row(item, "scheduled_at"),
                    "notes": _row(item, "notes"),
                }
                for item in contents
            ],
        })
    return result
