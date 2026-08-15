import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

import app
import runtime_guard
from conversation_layer import handle_callback as handle_context_callback, handle_message as handle_context_message, install as install_conversation_layer
from natural_behavior_patch import handle_explicit_simple_reminder, install_recurrence_patch, remember_after_message
from performance_patch import install_performance_patches
from quality_patch import handle_message as handle_quality_message, install as install_quality_patch
from reference_patch import handle_reference
from routine_integration import install_routine_integration
from scheduler_patch import install_scheduler_patches
from settings import OWNER_CHAT_ID

install_performance_patches()
install_scheduler_patches()
install_routine_integration()
install_conversation_layer()
install_quality_patch()
install_recurrence_patch()


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
                    "routine_agenda": True,
                    "natural_add_intents": True,
                    "contextual_conversation": True,
                    "inline_actions": True,
                    "smart_agenda": True,
                    "flexible_routines": True,
                    "simple_reminders": True,
                    "natural_references": True,
                    "task_reminder_minutes": 10,
                    "appointment_reminder_minutes": 5,
                    "informal_grocery": True,
                    "late_routine_confirmation": True,
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
            callback = update.get("callback_query")
            if callback:
                await handle_context_callback(self.env.DB, token, callback)
                return Response("ok")

            message = update.get("message") or update.get("edited_message")
            if message:
                handled = await handle_explicit_simple_reminder(self.env.DB, token, message)
                if not handled:
                    handled = await handle_reference(self.env.DB, token, message)
                # Estado ativo (rotina/tarefa em andamento) tem prioridade sobre inferência genérica.
                if not handled:
                    handled = await runtime_guard.handle_pre_dispatch(self.env.DB, token, message)
                if not handled:
                    handled = await handle_quality_message(self.env.DB, token, message)
                if not handled:
                    handled = await handle_context_message(self.env.DB, token, message)
                if not handled:
                    await app.handle_message(self.env.DB, token, message)
                    await remember_after_message(self.env.DB, message)
            return Response("ok")

        return Response("Not found", status=404)

    async def scheduled(self, controller, env, ctx):
        await app.scheduled_tick(self.env.DB, self.env.TELEGRAM_BOT_TOKEN)
