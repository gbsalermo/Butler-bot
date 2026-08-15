import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from app import handle_message, scheduled_tick
from performance_patch import install_performance_patches
from runtime_guard import handle_pre_dispatch
from scheduler_patch import install_scheduler_patches
from settings import OWNER_CHAT_ID

install_performance_patches()
install_scheduler_patches()


def _optional_env(env, name):
    try:
        return getattr(env, name)
    except Exception:
        return None


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path

        if request.method == "GET" and path == "/health":
            return Response(
                json.dumps({
                    "ok": True,
                    "service": "butler-bot",
                    "runtime": "cloudflare-python-worker",
                    "d1": True,
                    "owner_chat_id_configured": OWNER_CHAT_ID is not None,
                    "dispatcher": "functional-v1",
                    "webhook_secret_configured": bool(_optional_env(self.env, "TELEGRAM_WEBHOOK_SECRET")),
                    "fast_path": True,
                }),
                headers={"Content-Type": "application/json; charset=utf-8"},
            )

        if request.method == "POST" and path == "/telegram/webhook":
            webhook_secret = _optional_env(self.env, "TELEGRAM_WEBHOOK_SECRET")
            if webhook_secret:
                supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
                if supplied != webhook_secret:
                    return Response("forbidden", status=403)

            try:
                update = await request.json()
            except Exception:
                return Response("invalid json", status=400)

            token = self.env.TELEGRAM_BOT_TOKEN
            message = update.get("message") or update.get("edited_message")
            if message:
                handled = await handle_pre_dispatch(self.env.DB, token, message)
                if not handled:
                    await handle_message(self.env.DB, token, message)
            return Response("ok")

        return Response("Not found", status=404)

    async def scheduled(self, controller, env, ctx):
        await scheduled_tick(self.env.DB, self.env.TELEGRAM_BOT_TOKEN)
