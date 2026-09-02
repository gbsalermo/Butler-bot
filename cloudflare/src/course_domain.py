"""Domínio autoritativo de Cursos e Trilhas — Etapa 4.

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
_UNSET = object()


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
        payload = (
            json.dumps(detail, ensure_ascii=False, separators=(",", ":"))
            if not isinstance(detail, str)
            else detail
        )
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


async def list_courses(db, user_id, *, statuses=None):
    """Lista somente cursos do usuário, com filtro opcional de estados."""
    if statuses is None:
        statuses = ("active", "paused", "completed")
    statuses = tuple(str(item).strip() for item in statuses)
    if not statuses:
        return []
    if any(item not in COURSE_STATUSES for item in statuses):
        raise ValueError("invalid course status")
    placeholders = ",".join("?" for _ in statuses)
    return await _rows(
        db.prepare(
            "SELECT id,title,mode,status,description,created_at,updated_at,completed_at "
            f"FROM courses WHERE user_id=? AND status IN ({placeholders}) "
            "ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'paused' THEN 1 "
            "WHEN 'completed' THEN 2 ELSE 3 END, title COLLATE NOCASE, id"
        ).bind(int(user_id), *statuses)
    )


async def get_course(db, user_id, course_id):
    """Retorna metadados do curso quando ele pertence ao usuário."""
    return await _owned_course(db, user_id, course_id)


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


async def update_course(
    db,
    user_id,
    course_id,
    *,
    title=None,
    mode=None,
    description=_UNSET,
):
    """Edita metadados básicos sem alterar progresso ou estrutura."""
    current = await _owned_course(db, user_id, course_id)
    if not current:
        raise LookupError("course not found")

    assignments = []
    values = []
    changed = {}

    if title is not None:
        cleaned = _clean_title(title)
        assignments.append("title=?")
        values.append(cleaned)
        changed["title"] = cleaned

    if mode is not None:
        mode = str(mode or "").strip()
        if mode not in COURSE_MODES:
            raise ValueError("invalid course mode")
        assignments.append("mode=?")
        values.append(mode)
        changed["mode"] = mode

    if description is not _UNSET:
        cleaned_description = _clean_optional(description)
        assignments.append("description=?")
        values.append(cleaned_description)
        changed["description"] = cleaned_description

    if not assignments:
        return False

    assignments.append("updated_at=CURRENT_TIMESTAMP")
    values.extend((int(course_id), int(user_id)))
    await db.prepare(
        "UPDATE courses SET " + ",".join(assignments) + " WHERE id=? AND user_id=?"
    ).bind(*values).run()
    await _event(db, course_id, "course_updated", detail=changed)
    return True


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


async def rename_module(db, user_id, course_id, module_id, title):
    module = await _owned_module(db, user_id, course_id, module_id)
    if not module:
        raise LookupError("module not found")
    title = _clean_title(title)
    await db.prepare(
        "UPDATE course_modules SET title=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND course_id=?"
    ).bind(title, int(module_id), int(course_id)).run()
    await _event(db, course_id, "module_renamed", module_id=module_id, detail={"title": title})
    return True


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
        int(module_id),
        int(position),
        title,
        kind,
        _clean_optional(scheduled_at, max_len=80),
        _clean_optional(notes),
    ).run()
    content_id = _last_row_id(result)
    if content_id is None:
        row = await db.prepare(
            "SELECT id FROM course_contents WHERE module_id=? AND position=?"
        ).bind(int(module_id), int(position)).first()
        content_id = int(_row(row, "id")) if row else None
    await _event(
        db,
        course_id,
        "content_added",
        module_id=module_id,
        content_id=content_id,
        detail={"position": int(position), "kind": kind},
    )
    return content_id


async def update_content(
    db,
    user_id,
    course_id,
    content_id,
    *,
    title=None,
    kind=None,
    scheduled_at=_UNSET,
    notes=_UNSET,
):
    """Edita metadados do conteúdo; nunca altera o status de progresso."""
    content = await _owned_content(db, user_id, course_id, content_id)
    if not content:
        raise LookupError("content not found")

    assignments = []
    values = []
    changed = {}

    if title is not None:
        cleaned = _clean_title(title)
        assignments.append("title=?")
        values.append(cleaned)
        changed["title"] = cleaned

    if kind is not None:
        kind = str(kind or "").strip()
        if kind not in CONTENT_KINDS:
            raise ValueError("invalid content kind")
        assignments.append("kind=?")
        values.append(kind)
        changed["kind"] = kind

    if scheduled_at is not _UNSET:
        cleaned_schedule = _clean_optional(scheduled_at, max_len=80)
        assignments.append("scheduled_at=?")
        values.append(cleaned_schedule)
        changed["scheduled_at"] = cleaned_schedule

    if notes is not _UNSET:
        cleaned_notes = _clean_optional(notes)
        assignments.append("notes=?")
        values.append(cleaned_notes)
        changed["notes"] = cleaned_notes

    if not assignments:
        return False

    assignments.append("updated_at=CURRENT_TIMESTAMP")
    values.append(int(content_id))
    await db.prepare(
        "UPDATE course_contents SET " + ",".join(assignments) + " WHERE id=?"
    ).bind(*values).run()
    await _event(
        db,
        course_id,
        "content_updated",
        module_id=_row(content, "module_id"),
        content_id=content_id,
        detail=changed,
    )
    return True


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
    await _event(
        db,
        course_id,
        "material_added",
        module_id=_row(content, "module_id"),
        content_id=content_id,
        detail={"kind": kind},
    )
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
    await _event(
        db,
        course_id,
        "activity_added",
        module_id=_row(content, "module_id"),
        content_id=content_id,
        activity_id=activity_id,
    )
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
        db,
        course_id,
        f"content_{status}",
        module_id=_row(content, "module_id"),
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
        db,
        course_id,
        f"activity_{status}",
        module_id=_row(row, "module_id"),
        content_id=_row(row, "content_id"),
        activity_id=activity_id,
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
        result["modules"].append(
            {
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
            }
        )
    return result


async def content_details(db, user_id, course_id, content_id):
    content = await _owned_content(db, user_id, course_id, content_id)
    if not content:
        raise LookupError("content not found")
    module = await db.prepare(
        "SELECT id,position,title FROM course_modules WHERE id=?"
    ).bind(int(_row(content, "module_id"))).first()
    materials = await _rows(
        db.prepare(
            "SELECT id,position,title,kind,reference FROM course_materials "
            "WHERE content_id=? ORDER BY position,id"
        ).bind(int(content_id))
    )
    activities = await _rows(
        db.prepare(
            "SELECT id,position,title,status,notes FROM course_activities "
            "WHERE content_id=? ORDER BY position,id"
        ).bind(int(content_id))
    )
    return {
        "id": int(_row(content, "id")),
        "module_id": int(_row(content, "module_id")),
        "module_title": _row(module, "title"),
        "module_position": int(_row(module, "position", 0) or 0),
        "position": int(_row(content, "position")),
        "title": _row(content, "title"),
        "kind": _row(content, "kind"),
        "status": _row(content, "status"),
        "scheduled_at": _row(content, "scheduled_at"),
        "notes": _row(content, "notes"),
        "materials": [
            {
                "id": int(_row(item, "id")),
                "position": int(_row(item, "position")),
                "title": _row(item, "title"),
                "kind": _row(item, "kind"),
                "reference": _row(item, "reference"),
            }
            for item in materials
        ],
        "activities": [
            {
                "id": int(_row(item, "id")),
                "position": int(_row(item, "position")),
                "title": _row(item, "title"),
                "status": _row(item, "status"),
                "notes": _row(item, "notes"),
            }
            for item in activities
        ],
    }



async def _bulk_insert_rows(db, sql_prefix, rows, width, *, chunk_rows=None):
    """Executa INSERTs multi-row respeitando o limite de 100 parâmetros do D1."""
    if not rows:
        return
    width = int(width)
    if width < 1:
        raise ValueError("bulk insert width must be positive")

    # D1 aceita no máximo 100 parâmetros vinculados por query. Usamos 96 para
    # manter margem e reduzir o número total de queries por invocação no plano Free.
    safe_chunk_rows = max(1, 96 // width)
    if chunk_rows is None:
        chunk_rows = safe_chunk_rows
    else:
        chunk_rows = max(1, min(int(chunk_rows), safe_chunk_rows))

    for start in range(0, len(rows), int(chunk_rows)):
        chunk = rows[start:start + int(chunk_rows)]
        placeholders = ",".join(
            "(" + ",".join("?" for _ in range(width)) + ")" for _ in chunk
        )
        params = []
        for row in chunk:
            if len(row) != width:
                raise ValueError("bulk insert row width mismatch")
            params.extend(row)
        await db.prepare(sql_prefix + placeholders).bind(*params).run()


async def import_course_plan(db, user_id, plan):
    """Persiste uma importação validada em lotes globais, inclusive no D1 Free."""
    if not isinstance(plan, dict):
        raise ValueError("invalid course import plan")
    mode = str(plan.get("mode") or "").strip()
    if mode not in COURSE_MODES:
        raise ValueError("invalid course mode")
    modules = plan.get("modules") or []
    if not modules:
        raise ValueError("course import requires modules")

    # Valida a estrutura mínima antes de criar qualquer registro.
    for module in modules:
        _clean_title(module.get("title"))
        contents = module.get("contents") or []
        if not contents:
            raise ValueError("imported module has no contents")
        for content in contents:
            _clean_title(content.get("title"))
            kind = str(content.get("kind") or "lesson").strip()
            if kind not in CONTENT_KINDS:
                raise ValueError("invalid content kind")
            for material in content.get("materials") or []:
                _clean_title(material.get("title"))
                material_kind = str(material.get("kind") or "other").strip()
                if material_kind not in MATERIAL_KINDS:
                    raise ValueError("invalid material kind")
            for activity in content.get("activities") or []:
                _clean_title(activity.get("title"))

    course_id = await create_course(
        db,
        user_id,
        _clean_title(plan.get("title")),
        mode=mode,
        description=_clean_optional(plan.get("description")),
    )
    totals = {"modules": 0, "contents": 0, "materials": 0, "activities": 0}

    try:
        # 1) Insere todos os módulos em uma única sequência de lotes.
        module_rows = [
            (
                int(course_id),
                int(module_pos),
                _clean_title(module.get("title")),
                None,
            )
            for module_pos, module in enumerate(modules, 1)
        ]
        await _bulk_insert_rows(
            db,
            "INSERT INTO course_modules(course_id,position,title,description) VALUES ",
            module_rows,
            4,
        )
        totals["modules"] = len(module_rows)

        inserted_modules = await _rows(
            db.prepare(
                "SELECT id,position FROM course_modules WHERE course_id=? ORDER BY position"
            ).bind(int(course_id))
        )
        module_ids = {
            int(_row(row, "position")): int(_row(row, "id"))
            for row in inserted_modules
        }
        if len(module_ids) != len(modules):
            raise RuntimeError("course module mapping is incomplete")

        # 2) Insere conteúdos de todos os módulos globalmente. Isso evita pagar o
        # overhead de uma consulta de mapeamento para cada módulo separadamente.
        content_rows = []
        for module_pos, module in enumerate(modules, 1):
            module_id = module_ids[int(module_pos)]
            for content_pos, content in enumerate(module.get("contents") or [], 1):
                kind = str(content.get("kind") or "lesson").strip()
                content_rows.append((
                    int(module_id),
                    int(content_pos),
                    _clean_title(content.get("title")),
                    kind,
                    _clean_optional(content.get("scheduled_at"), max_len=80),
                    _clean_optional(content.get("notes")),
                ))

        await _bulk_insert_rows(
            db,
            "INSERT INTO course_contents(module_id,position,title,kind,scheduled_at,notes) VALUES ",
            content_rows,
            6,
        )
        totals["contents"] = len(content_rows)

        inserted_contents = await _rows(
            db.prepare(
                "SELECT ct.id,m.position AS module_position,ct.position AS content_position "
                "FROM course_contents ct JOIN course_modules m ON m.id=ct.module_id "
                "WHERE m.course_id=? ORDER BY m.position,ct.position"
            ).bind(int(course_id))
        )
        content_ids = {
            (
                int(_row(row, "module_position")),
                int(_row(row, "content_position")),
            ): int(_row(row, "id"))
            for row in inserted_contents
        }
        if len(content_ids) != len(content_rows):
            raise RuntimeError("course content mapping is incomplete")

        # 3) Materiais e atividades também são agrupados globalmente.
        material_rows = []
        activity_rows = []
        for module_pos, module in enumerate(modules, 1):
            for content_pos, content in enumerate(module.get("contents") or [], 1):
                content_id = content_ids[(int(module_pos), int(content_pos))]
                for material_pos, material in enumerate(content.get("materials") or [], 1):
                    material_rows.append((
                        int(content_id),
                        int(material_pos),
                        _clean_title(material.get("title")),
                        str(material.get("kind") or "other").strip(),
                        _clean_optional(material.get("reference"), max_len=4000),
                    ))
                for activity_pos, activity in enumerate(content.get("activities") or [], 1):
                    activity_rows.append((
                        int(content_id),
                        int(activity_pos),
                        _clean_title(activity.get("title")),
                        _clean_optional(activity.get("notes")),
                    ))

        await _bulk_insert_rows(
            db,
            "INSERT INTO course_materials(content_id,position,title,kind,reference) VALUES ",
            material_rows,
            5,
        )
        await _bulk_insert_rows(
            db,
            "INSERT INTO course_activities(content_id,position,title,notes) VALUES ",
            activity_rows,
            4,
        )
        totals["materials"] = len(material_rows)
        totals["activities"] = len(activity_rows)

        await _event(db, course_id, "course_imported", detail=totals)
        return course_id
    except Exception:
        await db.prepare("DELETE FROM courses WHERE id=? AND user_id=?").bind(
            int(course_id), int(user_id)
        ).run()
        raise

