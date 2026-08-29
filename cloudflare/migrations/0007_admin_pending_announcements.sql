PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS admin_pending_announcements (
    pending_key TEXT PRIMARY KEY,
    owner_chat_id INTEGER NOT NULL,
    target_user_id INTEGER,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_pending_owner_status
    ON admin_pending_announcements(owner_chat_id, status, created_at);
