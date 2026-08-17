import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

import app
import runtime_guard
from academic_intelligence import handle_message as handle_academic_message, install as install_academic_intelligence
from academic_polish import install as install_academic_polish
from alert_diagnostics import handle_message as handle_alert_diagnostics
from attendance_patch import handle_message as handle_attendance_message, install as install_attendance
from attendance_enhancement import ensure_schema as ensure_attendance_schema, handle_callback as handle_attendance_callback, install as install_attendance_enhancement
from attendance_management import handle_message as handle_attendance_management, install as install_attendance_management
from attendance_production_fix import dispatch_class_attendance_reliable, handle_message as handle_attendance_production_ui, install as install_attendance_production_fix
from companion_safe_fallback import handle_message as handle_fallback_message, is_priority_farewell
from conversation_layer import handle_callback as handle_context_callback, handle_message as handle_context_message, install as install_conversation_layer
from core_fast_path import handle_message as handle_core_fast_path
from exam_cancel_patch import handle_message as handle_exam_cancel, install as install_exam_cancel
from exam_phrase_patch import handle_message as handle_exam_phrase
from grocery_phrase_patch import handle_message as handle_grocery_phrase
from natural_behavior_patch import handle_explicit_simple_reminder, install_recurrence_patch, remember_after_message
from operational_menu import handle_message as handle_operational_menu, install as install_operational_menu
from performance_patch import install_performance_patches
from personality_variants import install as install_personality_variants
from quality_patch import handle_message as handle_quality_message, install as install_quality_patch
from reference_patch import handle_reference
from reliable_reminders import dispatch_due_reminders
from reliable_summaries import dispatch_summaries
from reminder_policy import install as install_reminder_policy
from routine_editing import handle_message as handle_routine_editing
from routine_integration import install_routine_integration, _routine_reminders
from routine_ui_patch import handle_message as handle_routine_ui, install as install_routine_ui
from scheduled_delivery_guard import install as install_scheduled_delivery_guard
from scheduler_patch import install_scheduler_patches
from scheduler_runtime import run_isolated
from settings import OWNER_CHAT_ID
from start_reset import handle_start_reset
from task_context_patch import handle_message as handle_task_context, install as install_task_context
from task_emoji_patch import install as install_task_emoji_patch
from telegram_api import send_message
from ux_bugfixes import handle_global_navigation, install as install_ux_bugfixes
from workout_progress_patch import handle_message as handle_workout_progress, install as install_workout_progress


install_performance_patches()
install_scheduler_patches()
install_routine_integration()
install_routine_ui()
install_conversation_layer()
install_quality_patch()
install_recurrence_patch()
install_academic_intelligence()
install_academic_polish()
install_exam_cancel()
install_personality_variants()
install_reminder_policy()
install_ux_bugfixes()
install_task_context()
install_attendance()
install_attendance_enhancement()
install_attendance_management()
install_attendance_production_fix()
install_task_emoji_patch()
install_workout_progress()
install_scheduled_delivery_guard()
install_operational_menu()


BASE_BUTTONS = {
    "🏠 Menu principal", "🌙 Day-off", "Chamar, Butler!", "🏠 Cotidiano",
    "➕ Adicionar", "✅ Tarefa", "📅 Compromisso", "🗓️ Hoje", "⏭️ Amanhã",
    "📆 Outra data", "🗓️ Próximos 7 dias", "📚 Histórico", "📖 Histórico diário",
    "🗂️ Histórico de tarefas", "🛒 Item faltando", "🛒 O que está faltando?",
    "➕ Item faltando", "➕ Adicionar item", "📋 Ver itens faltando", "✅ Tarefas",
    "📅 Compromissos", "📚 Matérias", "📚 Minhas matérias", "⚙️ Gerenciar matérias",
    "➕ Adicionar matéria", "🗑️ Remover matéria", "🚫 Trancar matéria", "✏️ Editar matéria",
    "📥 Importar grade por PDF/texto", "🧘 Rotinas", "🎯 Metas", "🏋️ Musculação",
    "🚀 Começar os trabalhos", "📅 Treino de hoje", "📝 Registrar série",
    "😕 Não consegui treinar hoje", "✅ Finalizar treino", "📈 Progresso",
    "🔄 Reiniciar treinos", "📥 Importar treino por PDF/texto", "🔁 Substituir exercício",
    "❌ Cancelar ação", "/cancelar",
}


def _optional_env(env, name):
    try:
        return getattr(env, name)
    except Exception:
        return None


async def _attendance_tick(db, token):
    await ensure_attendance_schema(db)
    await dispatch_class_attendance_reliable(db, token)


async def _use_base_only_when_needed(db, message):
    text = (message.get("text") or "").strip()
    if text.startswith("/start") or text in BASE_BUTTONS:
        return True
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    try:
        row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(int(chat_id)).first()
        if not row:
            return True
        try:
            uid = int(getattr(row, "id"))
        except Exception:
            uid = int(row["id"])
        state, _ = await app.get_state(db, uid)
        return bool(state)
    except Exception:
        return False


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
                    "dispatcher": "butler-operational-core-v3",
                    "operational_focus": True,
                    "operational_menu": True,
                    "finance_hidden_from_primary_menu": True,
                    "goals_hidden_from_primary_menu": False,
                    "broad_nlu_disabled": True,
                    "legacy_nlu_fallback_blocked": True,
                    "cultural_background_disabled": True,
                    "generic_library_dispatch_disabled": True,
                    "cross_domain_suggestions_disabled": True,
                    "generic_personal_memory_disabled": True,
                    "natural_action_phrases": True,
                    "short_context_actions": True,
                    "routine_agenda": True,
                    "routine_editing": True,
                    "routine_checkpoint_editing": True,
                    "routine_edit_button": True,
                    "simple_reminders": True,
                    "task_reminder_minutes": 0,
                    "appointment_reminder_minutes": 5,
                    "informal_grocery": True,
                    "informal_grocery_suffix": True,
                    "natural_agenda_queries": True,
                    "academic_exams": True,
                    "exam_reminders_days": [7, 3, 1, 0],
                    "full_routine_completion": True,
                    "sarcasm_v3": True,
                    "varied_reminder_personality": True,
                    "natural_exam_phrases": True,
                    "exam_cancel": True,
                    "exam_wizard_cancel": True,
                    "reliable_reminders": True,
                    "reliable_summaries": True,
                    "morning_summary_hour": "07:00",
                    "weekly_summary": "domingo 20:00",
                    "summary_grace_minutes": 60,
                    "isolated_scheduler": True,
                    "scheduler_signature_fixed": True,
                    "telegram_delivery_confirmation": True,
                    "alert_diagnostics": True,
                    "routine_scheduler_direct": True,
                    "reminder_grace_minutes": 10,
                    "single_reminder_policy": True,
                    "global_back_navigation": True,
                    "workout_exercise_progress": True,
                    "workout_auto_refresh_on_completion": True,
                    "workout_load_references": True,
                    "workout_daily_cardio": True,
                    "contextual_task_postpone": True,
                    "task_list_retention_hours": 24,
                    "task_list_ephemeral_numbering": True,
                    "task_agenda_emoji": "📝",
                    "attendance_tracking": True,
                    "attendance_class_prompt": True,
                    "attendance_limit_per_subject": True,
                    "attendance_duration_based": True,
                    "attendance_schema_guard": True,
                    "attendance_humor_thresholds": [30, 50, 75, 100],
                    "attendance_lost_when_over_limit": True,
                    "attendance_edit_limit": True,
                    "attendance_delete_absence": True,
                    "attendance_delete_confirmation": True,
                    "attendance_reliable_class_alerts": True,
                    "attendance_grace_minutes": 10,
                    "attendance_authoritative_menu": True,
                }),
                headers={"Content-Type": "application/json; charset=utf-8"},
            )

        if request.method == "POST" and path == "/telegram/webhook":
            webhook_secret = _optional_env(self.env, "TELEGRAM_WEBHOOK_SECRET")
            if webhook_secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != webhook_secret:
                return Response("forbidden", status=403)

            try:
                update = await request.json()
            except Exception:
                return Response("invalid json", status=400)

            token = self.env.TELEGRAM_BOT_TOKEN
            callback = update.get("callback_query")
            if callback:
                handled = await handle_attendance_callback(self.env.DB, token, callback)
                if not handled:
                    await handle_context_callback(self.env.DB, token, callback)
                return Response("ok")

            message = update.get("message") or update.get("edited_message")
            if message:
                text = (message.get("text") or "")

                handled = await handle_start_reset(self.env.DB, token, message)
                if handled:
                    return Response("ok")

                handled = await handle_alert_diagnostics(self.env.DB, token, message)
                if handled:
                    return Response("ok")

                if is_priority_farewell(text):
                    handled = await handle_fallback_message(self.env.DB, token, message)
                    if handled:
                        return Response("ok")

                for handler in (
                    handle_operational_menu,
                    handle_routine_ui,
                    handle_routine_editing,
                    handle_attendance_production_ui,
                    handle_global_navigation,
                ):
                    handled = await handler(self.env.DB, token, message)
                    if handled:
                        return Response("ok")

                handled = await handle_core_fast_path(self.env.DB, token, message)
                if handled:
                    return Response("ok")

                await ensure_attendance_schema(self.env.DB)
                for handler in (
                    handle_attendance_management,
                    handle_attendance_message,
                    handle_exam_cancel,
                    handle_exam_phrase,
                    handle_academic_message,
                ):
                    handled = await handler(self.env.DB, token, message)
                    if handled:
                        return Response("ok")

                for handler in (
                    handle_explicit_simple_reminder,
                    handle_reference,
                    handle_task_context,
                    runtime_guard.handle_pre_dispatch,
                    handle_grocery_phrase,
                    handle_quality_message,
                    handle_workout_progress,
                    handle_context_message,
                ):
                    handled = await handler(self.env.DB, token, message)
                    if handled:
                        return Response("ok")

                if await _use_base_only_when_needed(self.env.DB, message):
                    await app.handle_message(self.env.DB, token, message)
                    await remember_after_message(self.env.DB, message)
                else:
                    await send_message(
                        token,
                        int((message.get("chat") or {}).get("id")),
                        "🕴️ Não entendi o que você quer fazer. Tenta dizer de outro jeito ou usa os botões.",
                        reply_markup={"keyboard": app.MAIN_KB, "resize_keyboard": True},
                    )

            return Response("ok")

        return Response("Not found", status=404)

    async def scheduled(self, controller, env, ctx):
        token = self.env.TELEGRAM_BOT_TOKEN
        db = self.env.DB
        await run_isolated("daily_items", dispatch_due_reminders, db, token)
        await run_isolated("routines", _routine_reminders, db, token)
        await run_isolated("attendance", _attendance_tick, db, token)
        await run_isolated("summaries", dispatch_summaries, db, token)
        await run_isolated("legacy", app.scheduled_tick, db, token)
