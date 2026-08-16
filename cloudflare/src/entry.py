import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

import app
import runtime_guard
from academic_intelligence import handle_message as handle_academic_message, install as install_academic_intelligence
from academic_polish import install as install_academic_polish
from attendance_patch import dispatch_class_attendance, handle_message as handle_attendance_message, install as install_attendance
from attendance_enhancement import ensure_schema as ensure_attendance_schema, handle_callback as handle_attendance_callback, install as install_attendance_enhancement
from attendance_management import handle_message as handle_attendance_management, install as install_attendance_management
from butler_library import handle_message as handle_butler_library
from cooking_library import handle_message as handle_cooking_library
from library_recipe_queries import handle_message as handle_library_recipe_queries
from library_catalog_handler import handle_message as handle_library_catalog
from library_context_bridge import remember_library_reply
from conversation_layer import handle_callback as handle_context_callback, handle_message as handle_context_message, install as install_conversation_layer
from conversational_background import handle_message as handle_conversational_background
from cultural_background import handle_message as handle_cultural_background
from companion_safe_fallback import handle_message as handle_companion_message, is_priority_farewell
from companion_language_patch import handle_message as handle_companion_language_patch
from companion_life_context import handle_message as handle_companion_life_context
from companion_nlu_v2 import handle_message as handle_companion_nlu_v2
from compound_router import handle_message as handle_compound_message
from context_router import classify, allow_optional
from context_sync import sync_route
from core_fast_path import handle_message as handle_core_fast_path
from deterministic_memory import handle_message as handle_deterministic_memory
from exam_cancel_patch import handle_message as handle_exam_cancel, install as install_exam_cancel
from exam_phrase_patch import handle_message as handle_exam_phrase
from general_memory import handle_message as handle_general_memory
from grocery_phrase_patch import handle_message as handle_grocery_phrase
from natural_behavior_patch import handle_explicit_simple_reminder, install_recurrence_patch, remember_after_message
from performance_patch import install_performance_patches
from personal_profile import handle_message as handle_personal_profile
from personality_variants import install as install_personality_variants
from quality_patch import handle_message as handle_quality_message, install as install_quality_patch
from reference_patch import handle_reference
from reliable_reminders import dispatch_due_reminders
from reminder_policy import install as install_reminder_policy
from routine_integration import install_routine_integration, _routine_reminders
from scheduler_patch import install_scheduler_patches
from scheduler_runtime import run_isolated
from settings import OWNER_CHAT_ID
from study_plan_flow import handle_message as handle_study_plan_flow
from suggestion_engine import handle_message as handle_suggestion_engine
from task_context_patch import handle_message as handle_task_context, install as install_task_context
from task_emoji_patch import install as install_task_emoji_patch
from ux_bugfixes import handle_global_navigation, install as install_ux_bugfixes
from workout_progress_patch import handle_message as handle_workout_progress, install as install_workout_progress

install_performance_patches(); install_scheduler_patches(); install_routine_integration(); install_conversation_layer(); install_quality_patch(); install_recurrence_patch(); install_academic_intelligence(); install_academic_polish(); install_exam_cancel(); install_personality_variants(); install_reminder_policy(); install_ux_bugfixes(); install_task_context(); install_attendance(); install_attendance_enhancement(); install_attendance_management(); install_task_emoji_patch(); install_workout_progress()

def _optional_env(env,name):
    try:return getattr(env,name)
    except Exception:return None

async def _attendance_tick(db,token):
    await ensure_attendance_schema(db)
    await dispatch_class_attendance(db,token)

class Default(WorkerEntrypoint):
    async def fetch(self,request):
        parsed=urlparse(request.url); path=parsed.path
        if request.method=="GET" and path=="/health":
            return Response(json.dumps({"ok":True,"service":"butler-bot","runtime":"cloudflare-python-worker","d1":True,"owner_chat_id_configured":OWNER_CHAT_ID is not None,"dispatcher":"context-router-v8-core-fast-path","core_priority_fast_path":True,"compound_message_router":True,"fast_path":True,"structured_intent_parser":True,"central_context_router":True,"short_context_memory":True,"context_switch_invalidation":True,"library_short_context_bridge":True,"deterministic_personal_memory":True,"generic_personal_entities":True,"explicit_preference_memory":True,"personal_memory_map":True,"per_user_memory":True,"action_policy":True,"core_action_gateway":True,"cross_domain_suggestions":True,"problem_vs_action_policy":True,"generic_study_plan_flow":True,"conversational_background":True,"informal_portuguese_background":True,"core_domain_protection":True,"butler_library":True,"library_manifest":True,"library_common_index":True,"library_catalog_fallback":True,"cooking_books":True,"traditional_brazilian_cooking":True,"informal_cooking_queries":True,"library_context_actions":True,"companion_action_suggestions":True,"companion_social_mode":True,"companion_study_plan":True,"companion_everyday_context":True,"routine_agenda":True,"natural_add_intents":True,"inline_actions":True,"smart_agenda":True,"flexible_routines":True,"simple_reminders":True,"natural_references":True,"task_reminder_minutes":0,"appointment_reminder_minutes":5,"informal_grocery":True,"informal_grocery_suffix":True,"late_routine_confirmation":True,"natural_agenda_queries":True,"academic_exams":True,"exam_reminders_days":[7,3,1,0],"exam_agenda_section":True,"full_routine_completion":True,"sarcasm_v3":True,"varied_reminder_personality":True,"natural_exam_phrases":True,"exam_cancel":True,"exam_wizard_cancel":True,"reliable_reminders":True,"isolated_scheduler":True,"routine_scheduler_direct":True,"reminder_grace_minutes":10,"single_reminder_policy":True,"global_back_navigation":True,"workout_exercise_progress":True,"workout_auto_refresh_on_completion":True,"workout_load_references":True,"workout_daily_cardio":True,"contextual_task_postpone":True,"task_list_retention_hours":24,"task_list_ephemeral_numbering":True,"task_agenda_emoji":"📝","attendance_tracking":True,"attendance_class_prompt":True,"attendance_limit_per_subject":True,"attendance_duration_based":True,"attendance_schema_guard":True,"attendance_humor_thresholds":[30,50,75,100],"attendance_lost_when_over_limit":True,"attendance_edit_limit":True,"attendance_delete_absence":True,"attendance_delete_confirmation":True,"natural_greetings":True,"priority_farewells":True}),headers={"Content-Type":"application/json; charset=utf-8"})
        if request.method=="POST" and path=="/telegram/webhook":
            webhook_secret=_optional_env(self.env,"TELEGRAM_WEBHOOK_SECRET")
            if webhook_secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token")!=webhook_secret:return Response("forbidden",status=403)
            try:update=await request.json()
            except Exception:return Response("invalid json",status=400)
            token=self.env.TELEGRAM_BOT_TOKEN; callback=update.get("callback_query")
            if callback:
                handled=await handle_attendance_callback(self.env.DB,token,callback)
                if not handled:await handle_context_callback(self.env.DB,token,callback)
                return Response("ok")
            message=update.get("message") or update.get("edited_message")
            if message:
                text=(message.get("text") or ""); route=classify(text); chat_id=(message.get("chat") or {}).get("id")
                if is_priority_farewell(text):
                    handled=await handle_companion_message(self.env.DB,token,message)
                    if handled:return Response("ok")
                handled=await handle_core_fast_path(self.env.DB,token,message)
                if handled:return Response("ok")
                handled=await handle_compound_message(self.env.DB,token,message)
                if handled:return Response("ok")
                if chat_id is not None:
                    try:await sync_route(self.env.DB,int(chat_id),route,text)
                    except Exception:pass
                handled=await handle_global_navigation(self.env.DB,token,message)
                if not handled:
                    await ensure_attendance_schema(self.env.DB); handled=await handle_attendance_management(self.env.DB,token,message)
                if not handled:handled=await handle_attendance_message(self.env.DB,token,message)
                if not handled:handled=await handle_explicit_simple_reminder(self.env.DB,token,message)
                if not handled:handled=await handle_reference(self.env.DB,token,message)
                if not handled:handled=await handle_exam_cancel(self.env.DB,token,message)
                if not handled:handled=await handle_exam_phrase(self.env.DB,token,message)
                if not handled:handled=await handle_academic_message(self.env.DB,token,message)
                if not handled:handled=await handle_task_context(self.env.DB,token,message)
                if not handled:handled=await runtime_guard.handle_pre_dispatch(self.env.DB,token,message)
                if not handled:handled=await handle_grocery_phrase(self.env.DB,token,message)
                if not handled:handled=await handle_quality_message(self.env.DB,token,message)
                if not handled:handled=await handle_study_plan_flow(self.env.DB,token,message)
                if not handled:handled=await handle_general_memory(self.env.DB,token,message)
                if not handled:handled=await handle_deterministic_memory(self.env.DB,token,message)
                if not handled:handled=await handle_personal_profile(self.env.DB,token,message)
                if not handled:handled=await handle_companion_life_context(self.env.DB,token,message)
                if not handled:handled=await handle_suggestion_engine(self.env.DB,token,message)
                if not handled:handled=await handle_workout_progress(self.env.DB,token,message)
                library_handled=False
                if not handled and allow_optional(route,"cooking"):
                    handled=await handle_cooking_library(self.env.DB,token,message); library_handled=handled
                if not handled and allow_optional(route,"cooking"):
                    handled=await handle_library_recipe_queries(self.env.DB,token,message); library_handled=handled
                if not handled and allow_optional(route):
                    handled=await handle_butler_library(self.env.DB,token,message); library_handled=handled
                if not handled and allow_optional(route):
                    handled=await handle_library_catalog(self.env.DB,token,message); library_handled=handled
                if not handled and allow_optional(route):
                    handled=await handle_cultural_background(self.env.DB,token,message); library_handled=handled
                if library_handled and chat_id is not None:
                    try:await remember_library_reply(self.env.DB,int(chat_id),route,text)
                    except Exception:pass
                if not handled:handled=await handle_companion_language_patch(self.env.DB,token,message)
                if not handled:handled=await handle_companion_nlu_v2(self.env.DB,token,message)
                if not handled and allow_optional(route):handled=await handle_conversational_background(self.env.DB,token,message)
                if not handled:handled=await handle_companion_message(self.env.DB,token,message)
                if not handled:handled=await handle_context_message(self.env.DB,token,message)
                if not handled:
                    await app.handle_message(self.env.DB,token,message); await remember_after_message(self.env.DB,message)
            return Response("ok")
        return Response("Not found",status=404)

    async def scheduled(self,controller,env,ctx):
        db=self.env.DB; token=self.env.TELEGRAM_BOT_TOKEN
        # Cada bloco é independente: nenhuma exceção pode silenciar outro tipo de aviso.
        await run_isolated("daily_items",dispatch_due_reminders,db,token)
        await run_isolated("routines",_routine_reminders,db,token)
        await run_isolated("attendance",_attendance_tick,db,token)
        # Legado ainda cuida de resumo, aulas e outras rotinas antigas. Se quebrar,
        # tarefas e rotinas acima já foram executadas independentemente.
        await run_isolated("legacy",app.scheduled_tick,db,token)
