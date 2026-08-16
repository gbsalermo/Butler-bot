CREATE TABLE IF NOT EXISTS conversation_context (
    user_id INTEGER PRIMARY KEY,
    topics_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversation_context_updated_at
    ON conversation_context(updated_at);
