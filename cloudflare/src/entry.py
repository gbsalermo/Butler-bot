import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from owner_profile import DEFAULT_FINANCE_LIMITS, OWNER_SUBJECTS, is_owner, preferred_name_for
from settings import OWNER_CHAT_ID
from telegram_api import send_message


async def _ensure_user(db, chat_id: int, user: dict) -> int:
    owner = 1 if is_owner(chat_id) else 0
    preferred = preferred_name_for(chat_id, user.get("first_name"))
    await db.prepare(
        """
        INSERT INTO users (telegram_chat_id, telegram_user_id, preferred_name, first_name, username, is_owner)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(telegram_chat_id) DO UPDATE SET
            telegram_user_id = excluded.telegram_user_id,
            first_name = excluded.first_name,
            username = excluded.username,
            is_owner = excluded.is_owner,
            updated_at = CURRENT_TIMESTAMP
        """
    ).bind(chat_id, user.get("id"), preferred, user.get("first_name"), user.get("username"), owner).run()

    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id = ?").bind(chat_id).first()
    user_id = int(row.id)
    await db.prepare(
        "INSERT OR IGNORE INTO assistant_state (user_id, day_off) VALUES (?, 0)"
    ).bind(user_id).run()
    await _seed_finance_limits(db, user_id)
    if owner:
        await _seed_owner_profile(db, user_id)
    return user_id


async def _seed_finance_limits(db, user_id: int):
    for category, limit in DEFAULT_FINANCE_LIMITS.items():
        await db.prepare(
            "INSERT OR IGNORE INTO finance_limits (user_id, category, monthly_limit) VALUES (?, ?, ?)"
        ).bind(user_id, category, limit).run()


async def _seed_owner_profile(db, user_id: int):
    for item in OWNER_SUBJECTS:
        await db.prepare(
            "INSERT OR IGNORE INTO subjects (user_id, name) VALUES (?, ?)"
        ).bind(user_id, item["name"]).run()
        subject = await db.prepare(
            "SELECT id FROM subjects WHERE user_id = ? AND name = ?"
        ).bind(user_id, item["name"]).first()
        exists = await db.prepare(
            """
            SELECT id FROM subject_sessions
            WHERE subject_id = ? AND weekday = ? AND start_time = ? AND end_time = ? AND COALESCE(location,'') = ?
            """
        ).bind(int(subject.id), item["weekday"], item["start"], item["end"], item["location"]).first()
        if not exists:
            await db.prepare(
                "INSERT INTO subject_sessions (subject_id, weekday, start_time, end_time, location) VALUES (?, ?, ?, ?, ?)"
            ).bind(int(subject.id), item["weekday"], item["start"], item["end"], item["location"]).run()


async def _start_message(db, chat_id: int, user: dict) -> str:
    await _ensure_user(db, chat_id, user)
    if is_owner(chat_id):
        return (
            "🕴️ Butler online, chefe. Seus dados pessoais estão vinculados a este chat_id.\n\n"
            "A infraestrutura Cloudflare ainda está em migração por etapas; o perfil e a persistência D1 já estão separados por usuário."
        )
    return (
        "🕴️ Butler online.\n\n"
        "Este é um perfil novo e limpo. Seus dados serão associados somente a este chat."
    )


async def _handle_message(db, token: str, message: dict):
    chat = message.get("chat") or {}
    user = message.get("from") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if chat_id is None:
        return

    await _ensure_user(db, int(chat_id), user)

    if text.startswith("/start"):
        reply = await _start_message(db, int(chat_id), user)
    elif text.startswith("/health"):
        reply = "✅ Butler Cloudflare está online."
    else:
        reply = (
            "🕴️ Recebi sua mensagem. A infraestrutura Cloudflare está ativa, mas este comando ainda não foi portado para o dispatcher de produção."
        )
    await send_message(token, int(chat_id), reply)


async def _run_scheduled(db, token: str):
    now = datetime.now(timezone.utc).isoformat()
    print(f"Butler scheduled tick: {now}")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path

        if request.method == "GET" and path == "/health":
            configured_owner = OWNER_CHAT_ID is not None
            return Response(
                json.dumps({
                    "ok": True,
                    "service": "butler-bot",
                    "runtime": "cloudflare-python-worker",
                    "d1": True,
                    "owner_chat_id_configured": configured_owner,
                }),
                headers={"Content-Type": "application/json; charset=utf-8"},
            )

        if request.method == "POST" and path == "/telegram/webhook":
            try:
                update = await request.json()
            except Exception:
                return Response("invalid json", status=400)

            token = self.env.TELEGRAM_BOT_TOKEN
            message = update.get("message") or update.get("edited_message")
            if message:
                await _handle_message(self.env.DB, token, message)
            return Response("ok")

        return Response("Not found", status=404)

    async def scheduled(self, controller, env, ctx):
        await _run_scheduled(self.env.DB, self.env.TELEGRAM_BOT_TOKEN)
