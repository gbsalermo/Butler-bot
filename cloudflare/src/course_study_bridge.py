"""Ponte Cursos ↔ Modo Estudo — Etapa 4.4.

A ponte cria uma sessão de estudo a partir de um conteúdo pendente e registra o
vínculo entre os dois domínios. Ela deliberadamente NÃO sincroniza conclusão:
terminar tópico, foco ou sessão continua sem concluir conteúdo de curso.
"""
from __future__ import annotations

import course_domain
import study_mode


class StudySessionBusy(RuntimeError):
    """Já existe uma sessão ativa/pausada para o usuário."""


async def ensure_schema(db):
    """Tolerância operacional; 0014_course_study_links.sql é a fonte formal."""
    await db.prepare(
        """
        CREATE TABLE IF NOT EXISTS course_study_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            study_session_id INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY(content_id) REFERENCES course_contents(id) ON DELETE CASCADE,
            FOREIGN KEY(study_session_id) REFERENCES study_sessions(id) ON DELETE CASCADE
        )
        """
    ).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_course_study_links_user_content "
        "ON course_study_links(user_id,course_id,content_id,created_at)"
    ).run()


async def start_content_study(db, user_id, course_id, content_id, *, now=None):
    """Inicia Modo Estudo para um conteúdo pendente sem mudar seu progresso."""
    course = await course_domain.get_course(db, user_id, course_id)
    if not course:
        raise LookupError("course not found")
    if course_domain._row(course, "status") != "active":
        raise ValueError("course must be active")

    detail = await course_domain.content_details(db, user_id, course_id, content_id)
    if detail["status"] != "pending":
        raise ValueError("content must be pending")

    await study_mode.ensure_schema(db)
    active = await study_mode._active_session(db, user_id)
    if active:
        raise StudySessionBusy("study session already active")

    config = {
        "focus_minutes": study_mode.DEFAULT_FOCUS_MINUTES,
        "break_minutes": study_mode.DEFAULT_BREAK_MINUTES,
        "long_break_minutes": study_mode.DEFAULT_LONG_BREAK_MINUTES,
        "long_break_every": study_mode.DEFAULT_LONG_BREAK_EVERY,
    }
    session, topic = await study_mode._create_session(
        db,
        int(user_id),
        str(course_domain._row(course, "title")),
        [detail["title"]],
        config,
        now=now,
    )
    session_id = int(study_mode._row(session, "id"))

    await ensure_schema(db)
    await db.prepare(
        "INSERT INTO course_study_links(user_id,course_id,content_id,study_session_id) VALUES(?,?,?,?)"
    ).bind(int(user_id), int(course_id), int(content_id), session_id).run()
    await course_domain._event(
        db,
        course_id,
        "course_study_started",
        module_id=detail["module_id"],
        content_id=content_id,
        detail={"study_session_id": session_id},
    )

    return {
        "session_id": session_id,
        "topic_id": int(study_mode._row(topic, "id")) if topic else None,
        "subject": str(course_domain._row(course, "title")),
        "content_title": detail["title"],
        "focus_minutes": config["focus_minutes"],
    }


async def links_for_content(db, user_id, course_id, content_id):
    """Histórico dos estudos disparados por um conteúdo pertencente ao usuário."""
    await course_domain.content_details(db, user_id, course_id, content_id)
    await ensure_schema(db)
    result = await db.prepare(
        "SELECT l.study_session_id,l.created_at,s.status,s.cycles_completed "
        "FROM course_study_links l JOIN study_sessions s ON s.id=l.study_session_id "
        "WHERE l.user_id=? AND l.course_id=? AND l.content_id=? ORDER BY l.id DESC"
    ).bind(int(user_id), int(course_id), int(content_id)).all()
    rows = getattr(result, "results", None) or []
    try:
        return list(rows)
    except Exception:
        return rows.to_py() if hasattr(rows, "to_py") else []
