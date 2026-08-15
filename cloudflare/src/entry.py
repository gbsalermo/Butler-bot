import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from app import handle_message, scheduled_tick
from settings import OWNER_CHAT_ID


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
                await handle_message(self.env.DB, token, message)
            return Response("ok")

        return Response("Not found", status=404)

    async def scheduled(self, controller, env, ctx):
        await scheduled_tick(self.env.DB, self.env.TELEGRAM_BOT_TOKEN)
