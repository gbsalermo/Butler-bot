PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS subject_attendance_settings (
    subject_id INTEGER PRIMARY KEY,
    absence_limit INTEGER,
    limit_prompted INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS subject_absences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    class_date TEXT NOT NULL,
    absence_count INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, session_id, class_date),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY(session_id) REFERENCES subject_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_absences_user_subject
    ON subject_absences(user_id, subject_id, class_date);
