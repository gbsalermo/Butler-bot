CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject_name TEXT NOT NULL,
    focus_minutes INTEGER NOT NULL DEFAULT 25,
    break_minutes INTEGER NOT NULL DEFAULT 5,
    long_break_minutes INTEGER NOT NULL DEFAULT 15,
    long_break_every INTEGER NOT NULL DEFAULT 4,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','paused','completed','cancelled')),
    phase TEXT NOT NULL DEFAULT 'focus' CHECK(phase IN ('focus','break','long_break','paused','completed','cancelled')),
    phase_ends_at TEXT,
    cycles_completed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    cancelled_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_study_sessions_user_status
ON study_sessions(user_id, status, phase_ends_at);

CREATE TABLE IF NOT EXISTS study_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','completed','skipped')),
    completed_at TEXT,
    skipped_at TEXT,
    FOREIGN KEY(session_id) REFERENCES study_sessions(id) ON DELETE CASCADE,
    UNIQUE(session_id, position)
);

CREATE INDEX IF NOT EXISTS idx_study_topics_session_status
ON study_topics(session_id, status, position);

CREATE TABLE IF NOT EXISTS study_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    topic_id INTEGER,
    event_type TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES study_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(topic_id) REFERENCES study_topics(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_study_events_session_created
ON study_events(session_id, created_at, id);
