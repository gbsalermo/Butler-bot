PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ru_menu_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_start TEXT NOT NULL,
    week_end TEXT NOT NULL,
    source_filename TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, week_start)
);

CREATE TABLE IF NOT EXISTS ru_menu_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    import_id INTEGER,
    meal_date TEXT NOT NULL,
    meal_type TEXT NOT NULL,
    item_label TEXT NOT NULL,
    item_value TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(import_id) REFERENCES ru_menu_imports(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ru_menu_user_date
ON ru_menu_entries(user_id, meal_date, meal_type, position);
