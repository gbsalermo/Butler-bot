CREATE TABLE IF NOT EXISTS quick_timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('timer','quick_alert')),
    label TEXT NOT NULL,
    delay_seconds INTEGER NOT NULL CHECK(delay_seconds > 0),
    fire_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','fired','cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fired_at TEXT,
    cancelled_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quick_timers_user_status_fire
ON quick_timers(user_id, status, fire_at);
