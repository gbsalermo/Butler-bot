"""Autoridade de domínio da Etapa 4 para cursos e trilhas.

Esta camada não conversa com Telegram e não interpreta linguagem natural. Ela
valida identidade, ordenação, propriedade e transições de progresso. Menus,
importadores e Modo Estudo devem chamar estas operações em vez de escrever nas
tabelas de cursos diretamente.

Invariante central: progresso só muda por chamada explícita de domínio. Tempo
decorrido, scheduler ou fim de sessão de estudo nunca concluem conteúdo.
"""
from __future__ import annotations

import json

COURSE_MODES = {"self_paced", "live"}
COURSE_STATUSES = {"active", "completed", "archived"}
CONTENT_TYPES = {"lesson", "activity", "material", "other"}
PROGRESS_STATUSES = {"pending", "in_progress", "completed", "skipped"}

_SCHEMA_READY = False


class CourseDomainError(ValueError):
    """Erro de regra de negócio seguro para camadas de apresentação."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


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


def _dict(row):
    if row is None:
        return None
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    try:
        return dict(row)
    except Exception:
        return row


def _clean_text(value, field, *, max_len=180, required=True):
    text = " ".join(str(value or "").split()).strip()
    if required and not text:
        raise CourseDomainError("invalid_text", f"{field} não pode ficar vazio.")
    if len(text) > max_len:
        raise CourseDomainError("invalid_text", f"{field} passou do limite de {max_len} caracteres.")
    return text or None


def _last_row_id(result):
    meta = getattr(result, "meta", None)
    if meta is None:
        return None
    value = getattr(meta, "last_row_id", None)
    if value is None:
        try:
            value = meta["last_row_id"]
        except Exception:
            return None
    try:
        return int(value)
    except Exception:
        return None


async def ensure_schema(db):
    """Guard defensivo; migration 0013 continua sendo a fonte formal do D1."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    statements = [
        """CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            mode TEXT NOT NULL DEFAULT 'self_paced' CHECK(mode IN ('self_paced','live')),
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','completed','archived')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            archived_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_courses_user_status ON courses(user_id,status,updated_at,id)",
        """CREATE TABLE IF NOT EXISTS course_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            position INTEGER NOT NULL CHECK(position >= 1),
            title TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
            UNIQUE(course_id, position)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_course_modules_course_position ON course_modules(course_id,position,id)",
        """CREATE TABLE IF NOT EXISTS course_contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            position INTEGER NOT NULL CHECK(position >= 1),
            title TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'lesson' CHECK(content_type IN ('lesson','activity','material','other')),
            scheduled_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(module_id) REFERENCES course_modules(id) ON DELETE CASCADE,
            UNIQUE(module_id, position)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_course_contents_module_position ON course_contents(module_id,position,id)",
        """CREATE TABLE IF NOT EXISTS course_progress (
            content_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','in_progress','completed','skipped')),
            started_at TEXT,
            completed_at TEXT,
            skipped_at TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(content_id) REFERENCES course_contents(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_course_progress_status ON course_progress(status,updated_at,content_id)",
        """CREATE TRIGGER IF NOT EXISTS trg_course_contents_progress
            AFTER INSERT ON course_contents
            BEGIN
                INSERT OR IGNORE INTO course_progress(content_id,status) VALUES(NEW.id,'pending');
            END""",
        """CREATE TABLE IF NOT EXISTS course_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            module_id INTEGER,
            content_id INTEGER,
            event_type TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY(module_id) REFERENCES course_modules(id) ON DELETE SET NULL,
            FOREIGN KEY(content_id) REFERENCES course_contents(id) ON DELETE SET NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_course_events_course_created ON course_events(course_id,created_at,id)",
    ]
    for sql in statements:
        await db.prepare(sql).run()
    _SCHEMA_READY = True


async def _log(db, course_id, event_type, *, module_id=None, content_id=None, detail=None):
    await db.prepare(
        "INSERT INTO course_events(course_id,module_id,content_id,event_type,detail) VALUES(?,?,?,?,?)"
    ).bind(
        int(course_id),
        int(module_id) if module_id is not None else None,
        int(content_id) if content_id is not None else None,
        str(event_type),
        json.dumps(detail or {}, ensure_ascii=False, separators=(",", ":")),
    ).run()


async def get_course(db, user_id, course_id):
    await ensure_schema(db)
    row = await db.prepare(
        "SELECT * FROM courses WHERE id=? AND user_id=?"
    ).bind(int(course_id), int(user_id)).first()
    if not row:
        raise CourseDomainError("course_not_found", "Curso não encontrado para este usuário.")
    return row


async def _active_course(db, user_id, course_id):
    course = await get_course(db, user_id, course_id)
    if _row(course, "status") != "active":
        raise CourseDomainError("course_not_active", "Este curso não está ativo para edição/progresso.")
    return course


async def _module_for_user(db, user_id, module_id):
    await ensure_schema(db)
    row = await db.prepare(
        """SELECT m.*, c.user_id, c.status AS course_status, c.mode AS course_mode
           FROM course_modules m
           JOIN courses c ON c.id=m.course_id
           WHERE m.id=? AND c.user_id=?"""
    ).bind(int(module_id), int(user_id)).first()
    if not row:
        raise CourseDomainError("module_not_found", "Módulo não encontrado para este usuário.")
    return row


async def _content_for_user(db, user_id, content_id):
    await ensure_schema(db)
    row = await db.prepare(
        """SELECT cc.*, cp.status AS progress_status, cp.started_at, cp.completed_at, cp.skipped_at,
                  m.course_id, m.position AS module_position, c.user_id,
                  c.status AS course_status, c.mode AS course_mode
           FROM course_contents cc
           JOIN course_modules m ON m.id=cc.module_id
           JOIN courses c ON c.id=m.course_id
           LEFT JOIN course_progress cp ON cp.content_id=cc.id
           WHERE cc.id=? AND c.user_id=?"""
    ).bind(int(content_id), int(user_id)).first()
    if not row:
        raise CourseDomainError("content_not_found", "Conteúdo não encontrado para este usuário.")
    return row


async def create_course(db, user_id, title, *, mode="self_paced", description=None):
    await ensure_schema(db)
    title = _clean_text(title, "Nome do curso")
    description = _clean_text(description, "Descrição", max_len=1000, required=False)
    mode = str(mode or "self_paced").strip().lower()
    if mode not in COURSE_MODES:
        raise CourseDomainError("invalid_mode", "Modo de curso inválido. Use self_paced ou live.")

    result = await db.prepare(
        "INSERT INTO courses(user_id,title,description,mode,status) VALUES(?,?,?,?,'active')"
    ).bind(int(user_id), title, description, mode).run()
    course_id = _last_row_id(result)
    if course_id is None:
        row = await db.prepare(
            "SELECT id FROM courses WHERE user_id=? ORDER BY id DESC LIMIT 1"
        ).bind(int(user_id)).first()
        course_id = int(_row(row, "id"))
    await _log(db, course_id, "course_created", detail={"mode": mode, "title": title})
    return await get_course(db, user_id, course_id)


async def list_courses(db, user_id, *, status=None):
    await ensure_schema(db)
    if status is not None:
        status = str(status).strip().lower()
        if status not in COURSE_STATUSES:
            raise CourseDomainError("invalid_status", "Status de curso inválido.")
        return await _rows(
            db.prepare(
                "SELECT * FROM courses WHERE user_id=? AND status=? ORDER BY updated_at DESC,id DESC"
            ).bind(int(user_id), status)
        )
    return await _rows(
        db.prepare("SELECT * FROM courses WHERE user_id=? ORDER BY updated_at DESC,id DESC").bind(int(user_id))
    )


async def add_module(db, user_id, course_id, title, *, description=None):
    course = await _active_course(db, user_id, course_id)
    title = _clean_text(title, "Nome do módulo")
    description = _clean_text(description, "Descrição", max_len=1000, required=False)
    pos_row = await db.prepare(
        "SELECT COALESCE(MAX(position),0)+1 AS next_position FROM course_modules WHERE course_id=?"
    ).bind(int(course_id)).first()
    position = int(_row(pos_row, "next_position", 1))
    result = await db.prepare(
        "INSERT INTO course_modules(course_id,position,title,description) VALUES(?,?,?,?)"
    ).bind(int(course_id), position, title, description).run()
    module_id = _last_row_id(result)
    if module_id is None:
        row = await db.prepare(
            "SELECT id FROM course_modules WHERE course_id=? ORDER BY position DESC,id DESC LIMIT 1"
        ).bind(int(course_id)).first()
        module_id = int(_row(row, "id"))
    await _log(
        db, int(_row(course, "id")), "module_added",
        module_id=module_id, detail={"position": position, "title": title},
    )
    return await _module_for_user(db, user_id, module_id)


async def add_content(
    db,
    user_id,
    module_id,
    title,
    *,
    content_type="lesson",
    scheduled_at=None,
):
    module = await _module_for_user(db, user_id, module_id)
    if _row(module, "course_status") != "active":
        raise CourseDomainError("course_not_active", "Este curso não está ativo para receber conteúdo.")
    title = _clean_text(title, "Nome do conteúdo")
    content_type = str(content_type or "lesson").strip().lower()
    if content_type not in CONTENT_TYPES:
        raise CourseDomainError("invalid_content_type", "Tipo de conteúdo inválido.")
    scheduled_at = _clean_text(scheduled_at, "Data agendada", max_len=80, required=False)

    pos_row = await db.prepare(
        "SELECT COALESCE(MAX(position),0)+1 AS next_position FROM course_contents WHERE module_id=?"
    ).bind(int(module_id)).first()
    position = int(_row(pos_row, "next_position", 1))
    result = await db.prepare(
        "INSERT INTO course_contents(module_id,position,title,content_type,scheduled_at) VALUES(?,?,?,?,?)"
    ).bind(int(module_id), position, title, content_type, scheduled_at).run()
    content_id = _last_row_id(result)
    if content_id is None:
        row = await db.prepare(
            "SELECT id FROM course_contents WHERE module_id=? ORDER BY position DESC,id DESC LIMIT 1"
        ).bind(int(module_id)).first()
        content_id = int(_row(row, "id"))
    await _log(
        db, int(_row(module, "course_id")), "content_added",
        module_id=int(module_id), content_id=content_id,
        detail={"position": position, "title": title, "content_type": content_type, "scheduled_at": scheduled_at},
    )
    return await _content_for_user(db, user_id, content_id)


async def get_outline(db, user_id, course_id):
    course = await get_course(db, user_id, course_id)
    modules = await _rows(
        db.prepare("SELECT * FROM course_modules WHERE course_id=? ORDER BY position,id").bind(int(course_id))
    )
    output = {"course": _dict(course), "modules": []}
    for module in modules:
        contents = await _rows(
            db.prepare(
                """SELECT cc.*, COALESCE(cp.status,'pending') AS progress_status,
                          cp.started_at,cp.completed_at,cp.skipped_at
                   FROM course_contents cc
                   LEFT JOIN course_progress cp ON cp.content_id=cc.id
                   WHERE cc.module_id=? ORDER BY cc.position,cc.id"""
            ).bind(int(_row(module, "id")))
        )
        output["modules"].append({
            "module": _dict(module),
            "contents": [_dict(item) for item in contents],
        })
    return output


async def get_next_content(db, user_id, course_id):
    await get_course(db, user_id, course_id)
    return await db.prepare(
        """SELECT cc.*, COALESCE(cp.status,'pending') AS progress_status,
                  m.course_id,m.position AS module_position,m.title AS module_title
           FROM course_modules m
           JOIN course_contents cc ON cc.module_id=m.id
           LEFT JOIN course_progress cp ON cp.content_id=cc.id
           WHERE m.course_id=? AND COALESCE(cp.status,'pending') IN ('pending','in_progress')
           ORDER BY CASE COALESCE(cp.status,'pending') WHEN 'in_progress' THEN 0 ELSE 1 END,
                    m.position,cc.position,cc.id
           LIMIT 1"""
    ).bind(int(course_id)).first()


async def start_content(db, user_id, content_id):
    content = await _content_for_user(db, user_id, content_id)
    if _row(content, "course_status") != "active":
        raise CourseDomainError("course_not_active", "O curso precisa estar ativo para iniciar conteúdo.")
    status = _row(content, "progress_status") or "pending"
    if status in {"completed", "skipped"}:
        raise CourseDomainError("content_finished", "Este conteúdo já foi encerrado.")
    if status == "in_progress":
        return content

    other = await db.prepare(
        """SELECT cc.id
           FROM course_modules m
           JOIN course_contents cc ON cc.module_id=m.id
           JOIN course_progress cp ON cp.content_id=cc.id
           WHERE m.course_id=? AND cp.status='in_progress' AND cc.id<>?
           LIMIT 1"""
    ).bind(int(_row(content, "course_id")), int(content_id)).first()
    if other:
        raise CourseDomainError(
            "another_content_in_progress",
            "Já existe outro conteúdo em andamento neste curso.",
        )

    await db.prepare(
        """UPDATE course_progress
           SET status='in_progress',started_at=COALESCE(started_at,CURRENT_TIMESTAMP),updated_at=CURRENT_TIMESTAMP
           WHERE content_id=? AND status='pending'"""
    ).bind(int(content_id)).run()
    await _log(
        db, int(_row(content, "course_id")), "content_started",
        module_id=int(_row(content, "module_id")), content_id=int(content_id),
    )
    return await _content_for_user(db, user_id, content_id)


async def complete_content(db, user_id, content_id):
    content = await _content_for_user(db, user_id, content_id)
    if _row(content, "course_status") != "active":
        raise CourseDomainError("course_not_active", "O curso precisa estar ativo para concluir conteúdo.")
    status = _row(content, "progress_status") or "pending"
    if status == "completed":
        return content
    if status == "skipped":
        raise CourseDomainError("content_skipped", "Conteúdo pulado precisa ser reaberto antes de ser concluído.")

    await db.prepare(
        """UPDATE course_progress
           SET status='completed',completed_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP
           WHERE content_id=? AND status IN ('pending','in_progress')"""
    ).bind(int(content_id)).run()
    await _log(
        db, int(_row(content, "course_id")), "content_completed",
        module_id=int(_row(content, "module_id")), content_id=int(content_id),
    )
    return await _content_for_user(db, user_id, content_id)


async def skip_content(db, user_id, content_id):
    content = await _content_for_user(db, user_id, content_id)
    if _row(content, "course_status") != "active":
        raise CourseDomainError("course_not_active", "O curso precisa estar ativo para pular conteúdo.")
    status = _row(content, "progress_status") or "pending"
    if status == "skipped":
        return content
    if status == "completed":
        raise CourseDomainError("content_completed", "Conteúdo concluído não pode ser pulado.")

    await db.prepare(
        """UPDATE course_progress
           SET status='skipped',skipped_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP
           WHERE content_id=? AND status IN ('pending','in_progress')"""
    ).bind(int(content_id)).run()
    await _log(
        db, int(_row(content, "course_id")), "content_skipped",
        module_id=int(_row(content, "module_id")), content_id=int(content_id),
    )
    return await _content_for_user(db, user_id, content_id)


async def progress_summary(db, user_id, course_id):
    await get_course(db, user_id, course_id)
    row = await db.prepare(
        """SELECT COUNT(cc.id) AS total,
                  SUM(CASE WHEN COALESCE(cp.status,'pending')='pending' THEN 1 ELSE 0 END) AS pending,
                  SUM(CASE WHEN cp.status='in_progress' THEN 1 ELSE 0 END) AS in_progress,
                  SUM(CASE WHEN cp.status='completed' THEN 1 ELSE 0 END) AS completed,
                  SUM(CASE WHEN cp.status='skipped' THEN 1 ELSE 0 END) AS skipped
           FROM course_modules m
           LEFT JOIN course_contents cc ON cc.module_id=m.id
           LEFT JOIN course_progress cp ON cp.content_id=cc.id
           WHERE m.course_id=?"""
    ).bind(int(course_id)).first()
    total = int(_row(row, "total", 0) or 0)
    completed = int(_row(row, "completed", 0) or 0)
    skipped = int(_row(row, "skipped", 0) or 0)
    terminal = completed + skipped
    return {
        "total": total,
        "pending": int(_row(row, "pending", 0) or 0),
        "in_progress": int(_row(row, "in_progress", 0) or 0),
        "completed": completed,
        "skipped": skipped,
        "terminal": terminal,
        "percent": round((terminal / total) * 100, 1) if total else 0.0,
    }


async def complete_course(db, user_id, course_id):
    course = await _active_course(db, user_id, course_id)
    summary = await progress_summary(db, user_id, course_id)
    if summary["total"] == 0:
        raise CourseDomainError("empty_course", "Curso sem conteúdos não pode ser concluído.")
    if summary["pending"] or summary["in_progress"]:
        raise CourseDomainError(
            "unfinished_contents",
            "Ainda existem conteúdos pendentes ou em andamento.",
        )
    await db.prepare(
        "UPDATE courses SET status='completed',completed_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?"
    ).bind(int(course_id), int(user_id)).run()
    await _log(db, int(course_id), "course_completed", detail=summary)
    return await get_course(db, user_id, int(_row(course, "id")))


async def archive_course(db, user_id, course_id):
    course = await get_course(db, user_id, course_id)
    if _row(course, "status") == "archived":
        return course
    await db.prepare(
        "UPDATE courses SET status='archived',archived_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?"
    ).bind(int(course_id), int(user_id)).run()
    await _log(db, int(course_id), "course_archived")
    return await get_course(db, user_id, course_id)
