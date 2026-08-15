import re

import app
import runtime_guard
from owner_profile import is_owner
from telegram_api import send_message


async def _uid(db, chat_id):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat_id).first()
    return int(app.rowget(row, "id")) if row else None


def _expected_sets(value):
    if value is None:
        return 0
    try:
        return int(value)
    except Exception:
        m = re.search(r"\d+", str(value))
        return int(m.group()) if m else 0


async def _set_count(db, uid, owner, week, exercise_name, target_date):
    if owner:
        row = await db.prepare(
            "SELECT COUNT(*) n FROM protocol_mass_set_logs "
            "WHERE user_id=? AND week=? AND weekday=? AND exercise_name=?"
        ).bind(uid, week or 1, app.WEEKDAY_NAMES[target_date.weekday()], exercise_name).first()
    else:
        row = await db.prepare(
            "SELECT COUNT(*) n FROM workout_set_logs "
            "WHERE user_id=? AND workout_date=? AND exercise_name=?"
        ).bind(uid, target_date.isoformat(), exercise_name).first()
    return int(app.rowget(row, "n", 0))


async def workout_text_with_progress(db, uid, owner):
    wd, week, active, exercises = await app.workout_plan(db, uid, owner)
    if owner and not active:
        return "🏋️ Os trabalhos ainda não começaram. Use 🚀 Começar os trabalhos quando quiser iniciar as 12 semanas."
    if not exercises:
        return f"🏋️ Não há treino cadastrado para {wd}."

    today = app.now_local().date()
    out = [f"🏋️ Treino de {wd.capitalize()}" + (f" — semana {week}/12" if week else "")]
    completed = 0

    for i, exercise in enumerate(exercises, 1):
        expected = _expected_sets(exercise.get("sets"))
        done = await _set_count(db, uid, owner, week, exercise["name"], today)
        finished = expected > 0 and done >= expected
        if finished:
            completed += 1

        extra = []
        if exercise.get("reps"):
            extra.append(str(exercise["reps"]))
        if exercise.get("load"):
            extra.append(str(exercise["load"]))
        suffix = (" — " + " • ".join(extra)) if extra else ""

        if expected:
            progress = f" [{min(done, expected)}/{expected}]"
        elif done:
            progress = f" [{done} série(s)]"
        else:
            progress = ""

        marker = "✅" if finished else "▫️"
        status = " — CONCLUÍDO" if finished else ""
        out.append(f"{marker} {i}. {exercise['name']} — {exercise.get('sets') or ''}{suffix}{progress}{status}")

    if completed:
        out.append(f"\nProgresso: {completed}/{len(exercises)} exercício(s) concluído(s).")
    return "\n".join(out)


async def handle_global_navigation(db, token, message):
    text = (message.get("text") or "").strip()
    if text != "⬅️ Voltar ao cotidiano":
        return False

    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return False
    uid = await _uid(db, int(chat_id))
    if not uid:
        return False

    # Limpa tanto estados do app quanto estados guard_* para que o botão nunca
    # seja interpretado como resposta de um fluxo anterior.
    await app.clear_state(db, uid)
    await runtime_guard._clear(db, uid)
    await send_message(
        token,
        int(chat_id),
        "🏠 Cotidiano. Voltamos ao painel antes que algum fluxo tente te manter em cárcere administrativo. 😌",
        reply_markup=app.kb(app.COTIDIANO_KB),
    )
    return True


def install():
    original_handle_state = app.handle_state
    app.workout_text = workout_text_with_progress

    async def handle_state_with_workout_completion(db, token, chat, uid, owner, state, payload, message):
        # Guarda o exercício antes que o handler original limpe o estado.
        exercise_name = payload.get("exercise") if state == "workout_series_data" else None
        week = payload.get("week") if state == "workout_series_data" else None

        handled = await original_handle_state(db, token, chat, uid, owner, state, payload, message)
        if not handled or state != "workout_series_data" or not exercise_name:
            return handled

        # Se a série recém-registrada fechou a quantidade prevista do exercício,
        # devolve imediatamente a ficha atualizada.
        _, plan_week, active, exercises = await app.workout_plan(db, uid, owner)
        target = next((e for e in exercises if app.norm(e.get("name")) == app.norm(exercise_name)), None)
        if not target:
            return handled

        expected = _expected_sets(target.get("sets"))
        if expected <= 0:
            return handled

        today = app.now_local().date()
        done = await _set_count(db, uid, owner, week or plan_week, exercise_name, today)
        if done >= expected:
            text = await workout_text_with_progress(db, uid, owner)
            await send_message(
                token,
                chat,
                f"🏁 {exercise_name}: {expected}/{expected} séries. Exercício fechado.\n\n{text}",
                reply_markup=app.kb(app.WORKOUT_KB),
            )
        return handled

    app.handle_state = handle_state_with_workout_completion
