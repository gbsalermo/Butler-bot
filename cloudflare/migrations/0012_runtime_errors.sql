-- Butler: diagnóstico persistente de exceções não tratadas do Worker.
-- Não armazena texto das conversas; apenas escopo, tipo, mensagem técnica e chat_id.

CREATE TABLE IF NOT EXISTS runtime_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    chat_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_runtime_errors_created
ON runtime_errors(created_at DESC, id DESC);
