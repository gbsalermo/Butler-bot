PRAGMA foreign_keys = ON;

-- Etapa 4.1: identidade do curso. O modo diferencia avanço autogerido de
-- calendário ao vivo; progresso de conteúdos fica separado em course_progress.
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    mode TEXT NOT NULL DEFAULT 'self_paced'
        CHECK(mode IN ('self_paced','live')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active','completed','archived')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    archived_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_courses_user_status
ON courses(user_id, status, updated_at, id);

CREATE TABLE IF NOT EXISTS course_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK(position >= 1),
    title TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE(course_id, position)
);

CREATE INDEX IF NOT EXISTS idx_course_modules_course_position
ON course_modules(course_id, position, id);

CREATE TABLE IF NOT EXISTS course_contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK(position >= 1),
    title TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'lesson'
        CHECK(content_type IN ('lesson','activity','material','other')),
    scheduled_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(module_id) REFERENCES course_modules(id) ON DELETE CASCADE,
    UNIQUE(module_id, position)
);

CREATE INDEX IF NOT EXISTS idx_course_contents_module_position
ON course_contents(module_id, position, id);

-- Progresso é separado da identidade do conteúdo para permitir edição futura
-- sem perder estado/histórico. Nenhum relógio altera esta tabela sozinho.
CREATE TABLE IF NOT EXISTS course_progress (
    content_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','in_progress','completed','skipped')),
    started_at TEXT,
    completed_at TEXT,
    skipped_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(content_id) REFERENCES course_contents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_course_progress_status
ON course_progress(status, updated_at, content_id);

-- Todo conteúdo nasce explicitamente pendente no mesmo INSERT lógico.
CREATE TRIGGER IF NOT EXISTS trg_course_contents_progress
AFTER INSERT ON course_contents
BEGIN
    INSERT OR IGNORE INTO course_progress(content_id, status)
    VALUES (NEW.id, 'pending');
END;

CREATE TABLE IF NOT EXISTS course_events (
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
);

CREATE INDEX IF NOT EXISTS idx_course_events_course_created
ON course_events(course_id, created_at, id);
