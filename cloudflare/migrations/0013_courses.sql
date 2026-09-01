-- Etapa 4.1 — Cursos e trilhas de estudo.
-- Progresso é sempre explícito. Ordem estrutural não implica conclusão.

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'self_paced' CHECK(mode IN ('self_paced','live')),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','paused','completed','archived')),
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_courses_user_status
ON courses(user_id, status, title);

CREATE TABLE IF NOT EXISTS course_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE(course_id, position)
);

CREATE INDEX IF NOT EXISTS idx_course_modules_course_position
ON course_modules(course_id, position);

CREATE TABLE IF NOT EXISTS course_contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'lesson' CHECK(kind IN ('lesson','reading','exercise','project','review','other')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','completed','skipped')),
    scheduled_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    skipped_at TEXT,
    FOREIGN KEY(module_id) REFERENCES course_modules(id) ON DELETE CASCADE,
    UNIQUE(module_id, position)
);

CREATE INDEX IF NOT EXISTS idx_course_contents_module_status_position
ON course_contents(module_id, status, position);

CREATE INDEX IF NOT EXISTS idx_course_contents_schedule
ON course_contents(scheduled_at, status);

CREATE TABLE IF NOT EXISTS course_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'other' CHECK(kind IN ('link','file','video','text','other')),
    reference TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(content_id) REFERENCES course_contents(id) ON DELETE CASCADE,
    UNIQUE(content_id, position)
);

CREATE INDEX IF NOT EXISTS idx_course_materials_content_position
ON course_materials(content_id, position);

CREATE TABLE IF NOT EXISTS course_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','completed','skipped')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    skipped_at TEXT,
    FOREIGN KEY(content_id) REFERENCES course_contents(id) ON DELETE CASCADE,
    UNIQUE(content_id, position)
);

CREATE INDEX IF NOT EXISTS idx_course_activities_content_status_position
ON course_activities(content_id, status, position);

CREATE TABLE IF NOT EXISTS course_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    module_id INTEGER,
    content_id INTEGER,
    activity_id INTEGER,
    event_type TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY(module_id) REFERENCES course_modules(id) ON DELETE SET NULL,
    FOREIGN KEY(content_id) REFERENCES course_contents(id) ON DELETE SET NULL,
    FOREIGN KEY(activity_id) REFERENCES course_activities(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_course_events_course_created
ON course_events(course_id, created_at, id);
