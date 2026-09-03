PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS inbox_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'text' CHECK(source IN ('text','button')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','converted','archived')),
    converted_domain TEXT,
    converted_target_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    converted_at TEXT,
    archived_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_inbox_user_status_created
    ON inbox_items(user_id, status, created_at DESC, id DESC);

-- Conversões para tarefa/compromisso precisam ser idempotentes mesmo se a mesma
-- atualização do Telegram for repetida após uma falha entre a criação do alvo e
-- a atualização da Inbox.
ALTER TABLE daily_items ADD COLUMN source_inbox_id INTEGER REFERENCES inbox_items(id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_items_source_inbox
    ON daily_items(source_inbox_id)
    WHERE source_inbox_id IS NOT NULL;
