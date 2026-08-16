async def ensure_runtime_schema(db):
    statements = [
        """CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            payload TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS workout_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            workout_date TEXT NOT NULL,
            weekday TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'feito',
            reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, workout_date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS workout_set_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            workout_date TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            set_number INTEGER NOT NULL,
            load TEXT,
            reps TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, workout_date, exercise_name, set_number),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS conversation_context (
            user_id INTEGER PRIMARY KEY,
            topics_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_workout_logs_user_date ON workout_logs(user_id, workout_date)",
        "CREATE INDEX IF NOT EXISTS idx_workout_sets_user_exercise ON workout_set_logs(user_id, exercise_name, workout_date)",
        "CREATE INDEX IF NOT EXISTS idx_conversation_context_updated_at ON conversation_context(updated_at)",
    ]
    for sql in statements:
        await db.prepare(sql).run()
