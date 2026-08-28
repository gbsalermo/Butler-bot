PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS weather_preferences (
    user_id INTEGER PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1,
    morning_enabled INTEGER NOT NULL DEFAULT 1,
    city TEXT,
    latitude REAL,
    longitude REAL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
