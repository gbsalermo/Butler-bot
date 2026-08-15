from owner_profile import is_owner
from telegram_api import send_message

GENERIC_WORKOUT_KB = [
    ["📅 Treino de hoje", "📝 Registrar série"],
    ["✅ Finalizar treino", "😕 Não consegui treinar hoje"],
    ["📈 Progresso", "🔄 Reiniciar treinos"],
    ["📥 Importar treino por PDF/texto"],
    ["🏠 Menu principal"],
]


def _kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}


async def ensure_runtime_schema(db):
    """Garante as tabelas adicionadas após o schema inicial.

    Mantém o Worker tolerante a deploy antes da aplicação manual da migration 0002.
    As instruções são idempotentes e seguras para D1/SQLite.
    """
    await db.prepare(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            payload TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    ).run()
    await db.prepare(
        """
        CREATE TABLE IF NOT EXISTS workout_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            workout_date TEXT NOT NULL,
            weekday TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'feito',
            reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, workout_date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    ).run()
    await db.prepare(
        """
        CREATE TABLE IF NOT EXISTS workout_set_logs (
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
        )
        """
    ).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_workout_logs_user_date ON workout_logs(user_id, workout_date)"
    ).run()
    await db.prepare(
        "CREATE INDEX IF NOT EXISTS idx_workout_sets_user_exercise ON workout_set_logs(user_id, exercise_name, workout_date)"
    ).run()


async def handle_pre_dispatch(db, token: str, message: dict) -> bool:
    """Intercepta diferenças deliberadas entre o perfil pessoal e o genérico."""
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if chat_id is None or is_owner(int(chat_id)):
        return False

    if text == "🏋️ Musculação":
        await send_message(
            token,
            int(chat_id),
            "🏋️ Musculação\n\nSeu treino começa vazio. Importe uma ficha por PDF/texto ou use o acompanhamento depois que houver exercícios cadastrados. O protocolo pessoal de 12 semanas não é compartilhado com outros usuários.",
            reply_markup=_kb(GENERIC_WORKOUT_KB),
        )
        return True

    if text == "🚀 Começar os trabalhos":
        await send_message(
            token,
            int(chat_id),
            "Esse botão pertence ao protocolo pessoal do proprietário. No seu perfil, basta importar/cadastrar sua rotina e usar Treino de hoje. Nada do treino de outra pessoa é copiado para o seu chat.",
            reply_markup=_kb(GENERIC_WORKOUT_KB),
        )
        return True

    return False
