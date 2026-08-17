PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS goal_profiles (
    goal_id INTEGER PRIMARY KEY,
    goal_type TEXT NOT NULL CHECK(goal_type IN ('habit','numeric','project')),
    start_date TEXT NOT NULL,
    target_date TEXT,
    start_value REAL,
    current_value REAL,
    target_value REAL,
    unit TEXT,
    linked_routine_id INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT,
    completed_at TEXT,
    FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE CASCADE,
    FOREIGN KEY(linked_routine_id) REFERENCES routines(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_goal_profiles_status ON goal_profiles(status);
CREATE INDEX IF NOT EXISTS idx_goal_profiles_routine ON goal_profiles(linked_routine_id);
