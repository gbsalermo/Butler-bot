import sqlite3
from datetime import date, timedelta

from src.summary_engine import morning_summary
from src.user_scope import resolve_database_path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(resolve_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def _yesterday_block(target: date) -> str | None:
    yesterday = target - timedelta(days=1)

    with _connect() as conn:
        try:
            tasks = conn.execute(
                """
                SELECT title, status
                FROM daily_items
                WHERE kind = 'tarefa' AND due_date = ?
                ORDER BY id
                """,
                (yesterday.isoformat(),),
            ).fetchall()
            appointments = conn.execute(
                """
                SELECT COUNT(*)
                FROM daily_items
                WHERE kind = 'compromisso' AND due_date = ?
                """,
                (yesterday.isoformat(),),
            ).fetchone()[0]
            routines_done = conn.execute(
                """
                SELECT COUNT(DISTINCT routine_id)
                FROM routine_logs
                WHERE log_date = ? AND status = 'feito'
                """,
                (yesterday.isoformat(),),
            ).fetchone()[0]
        except sqlite3.OperationalError:
            return None

        workout_text = None
        try:
            state = conn.execute("SELECT * FROM protocol_mass_state WHERE id = 1").fetchone()
            if state and state["active"]:
                weekday_names = {
                    0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira",
                    3: "quinta-feira", 4: "sexta-feira", 5: "sábado", 6: "domingo",
                }
                weekday = weekday_names[yesterday.weekday()]
                if weekday != "domingo":
                    session = conn.execute(
                        """
                        SELECT completed_at, skipped_at
                        FROM protocol_mass_sessions
                        WHERE week = ? AND weekday = ?
                        """,
                        (int(state["current_week"]), weekday),
                    ).fetchone()
                    if session and session["completed_at"]:
                        workout_text = "🏋️ Treino na academia: concluído"
                    elif session and session["skipped_at"]:
                        workout_text = "🏋️ Treino na academia: falta registrada"
        except sqlite3.OperationalError:
            pass

    done = [row for row in tasks if row["status"] == "concluido"]
    pending = [row for row in tasks if row["status"] == "pendente"]

    # Se ontem não tinha nada relevante, não polui o resumo de hoje.
    if not tasks and not appointments and not routines_done and not workout_text:
        return None

    parts = ["📎 *Ontem, antes de fingirmos que nunca aconteceu:*", f"• ✅ Tarefas: *{len(done)}/{len(tasks)} concluídas*" if tasks else "• ✅ Nenhuma tarefa marcada"]
    if appointments:
        parts.append(f"• 📅 Compromissos: *{int(appointments)}*")
    if routines_done:
        parts.append(f"• 🧘 Rotinas cumpridas: *{int(routines_done)}*")
    if workout_text:
        parts.append(f"• {workout_text}")

    if pending:
        parts.append("\n👀 *Ficou pendente de ontem:*")
        for row in pending[:5]:
            parts.append(f"• {row['title']}")
        if len(pending) > 5:
            parts.append(f"• ...e mais {len(pending) - 5}. Sim, eu contei.")
        parts.append("Elas sobreviveram à virada do dia. Impressionante persistência. Vamos resolver isso.")
    elif tasks:
        parts.append("😏 Nenhuma tarefa de ontem ficou aberta. Eu notei. Não se acostume com elogios.")

    return "\n".join(parts)


def morning_summary_with_yesterday(name: str, target: date | None = None) -> str:
    target = target or date.today()
    today = morning_summary(name, target)
    yesterday = _yesterday_block(target)
    if not yesterday:
        return today
    return f"{today}\n\n{yesterday}"
