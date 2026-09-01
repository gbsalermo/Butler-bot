-- Etapa 4.4 — vínculo explícito entre Cursos e sessões do Modo Estudo.
-- A sessão de estudo nunca altera automaticamente o status do conteúdo.

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
);

CREATE INDEX IF NOT EXISTS idx_course_study_links_user_content
    ON course_study_links(user_id, course_id, content_id, created_at);
