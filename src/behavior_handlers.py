from datetime import datetime, timedelta

from telegram.ext import ApplicationHandlerStop, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from src.assistant_state import goal_progress_totals, list_routines
from src.behavior_engine import (
    goal_progress_comment,
    routine_done_comment,
    routine_streak,
    task_done_comment,
    task_snooze_comment,
    workout_absence_summary,
)
from src.daily_store import complete_item, snooze_item
from src.home_store import list_goals
from src.ui_layout import COTIDIANO_KEYBOARD


async def behavioral_daily_callback(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    parts = q.data.split(":")
    action, item_id = parts[0], int(parts[1])

    if action == "daily_done":
        # O comentário é calculado antes da conclusão para ainda enxergar atraso/adiamentos.
        comment = task_done_comment(item_id)
        complete_item(item_id)
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(f"✅ {comment}")
        raise ApplicationHandlerStop

    if action == "daily_snooze":
        minutes = int(parts[2])
        snooze_item(item_id, (datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="minutes"))
        comment = task_snooze_comment(item_id)
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(f"⏰ {comment}\nVolto em {minutes} minutos.")
        raise ApplicationHandlerStop


async def behavioral_routines_view(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_routines()
    if not rows:
        return

    parts = ["🧠 *O que eu tenho observado*", ""]
    interesting = False
    for row in rows:
        streak = routine_streak(int(row["id"]))
        if streak >= 2:
            interesting = True
            parts.append(f"• *{row['name']}*: {streak} dias seguidos")
            if streak >= 5:
                parts.append("  Não vou fazer festa, mas isso já está com cara de hábito.")

    if interesting:
        await update.message.reply_text("\n".join(parts), parse_mode="Markdown")
    # Não interrompe: a listagem normal vem logo depois.


async def behavioral_goals_view(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    totals = goal_progress_totals()
    if not totals:
        return
    comments = []
    for goal in totals:
        try:
            text = goal_progress_comment(int(goal["id"]))
        except Exception:
            continue
        if "dias" in text:
            comments.append(f"• *{goal['name']}*: {text}")
    if comments:
        await update.message.reply_text(
            "🧠 *Constância que eu notei*\n\n" + "\n".join(comments),
            parse_mode="Markdown",
        )


async def behavioral_protocol_progress(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count, last_reason = workout_absence_summary()
    if count <= 0:
        return
    if count == 1:
        text = "Uma falta registrada no protocolo até agora. Acontece. Só estou de olho para ela continuar sendo exceção."
    elif count == 2:
        text = "Duas faltas registradas no protocolo. Ainda tranquilo, mas eu já comecei a contar. Alguém precisa."
    else:
        text = f"{count} faltas registradas no protocolo. Não é bronca — é o número. E números têm esse péssimo hábito de não esquecer."
    if last_reason:
        text += f"\nÚltimo motivo: {last_reason}."
    await update.message.reply_text("🧠 " + text)


def register_behavior_handlers(application) -> None:
    # Vem antes do callback antigo para evitar dupla conclusão/adiamento.
    application.add_handler(
        CallbackQueryHandler(behavioral_daily_callback, pattern=r"^daily_(done|snooze):"),
        group=-20,
    )

    # Observações complementares: não bloqueiam as telas normais.
    application.add_handler(
        MessageHandler(filters.Regex(r"^📋 Ver rotinas$"), behavioral_routines_view),
        group=-9,
    )
    application.add_handler(
        MessageHandler(filters.Regex(r"^📊 Progresso das metas$"), behavioral_goals_view),
        group=-9,
    )
    application.add_handler(
        MessageHandler(filters.Regex(r"^📈 Progresso Protocol Mass$"), behavioral_protocol_progress),
        group=-9,
    )
