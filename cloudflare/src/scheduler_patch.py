from datetime import timedelta

import app
from owner_profile import is_owner


async def morning_summary_with_workout(db, uid, chat, token, today):
    text = await app.agenda_text(db, uid, today, True)
    grocery = await app.rows(
        db.prepare(
            "SELECT name FROM grocery_items WHERE user_id=? AND missing=1 ORDER BY name LIMIT 5"
        ).bind(uid)
    )
    extra = ""
    if grocery:
        extra += "\n\n🛒 Faltando em casa: " + ", ".join(
            app.rowget(row, "name") for row in grocery
        )

    yesterday = today - timedelta(days=1)
    pending = await app.rows(
        db.prepare(
            "SELECT title FROM daily_items WHERE user_id=? AND kind='tarefa' AND status='pendente' AND due_date=?"
        ).bind(uid, yesterday.isoformat())
    )
    if pending:
        extra += "\n\n📎 Ontem deixou herança:\n" + "\n".join(
            f"• {app.rowget(row, 'title')}" for row in pending
        )
        extra += "\nElas sobreviveram à virada do dia. Impressionante persistência."

    user = await db.prepare("SELECT telegram_chat_id FROM users WHERE id=?").bind(uid).first()
    owner = bool(user and is_owner(int(app.rowget(user, "telegram_chat_id"))))
    weekday, week, active, exercises = await app.workout_plan(db, uid, owner, today)
    if exercises and (not owner or active):
        label = f" — semana {week}/12" if owner and week else ""
        extra += f"\n\n🏋️ Treino na academia previsto hoje{label}: {len(exercises)} exercício(s)."

    await app.send(
        token,
        chat,
        "☀️ Resumo da manhã\n\n"
        + text
        + extra
        + "\n\nNada demais. Só a administração básica de uma pequena empresa chamada sua vida. 😌",
        app.MAIN_KB,
    )


def install_scheduler_patches():
    app.morning_summary = morning_summary_with_workout
