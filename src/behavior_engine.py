import re
import sqlite3
from datetime import date, datetime, timedelta

from src.user_scope import resolve_database_path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(resolve_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def _streak_from_dates(values: list[str]) -> int:
    days = sorted({date.fromisoformat(v) for v in values if v}, reverse=True)
    if not days:
        return 0
    today = date.today()
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    available = set(days)
    while cursor in available:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def task_postpone_count(item_id: int) -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COALESCE(postpone_count, 0) AS n FROM daily_items WHERE id = ?", (item_id,)).fetchone()
        return int(row["n"]) if row else 0


def task_context(item_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, title, due_date, due_time, COALESCE(postpone_count, 0) AS postpone_count FROM daily_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    if not row:
        return {"postpone_count": 0, "overdue": False, "title": ""}

    overdue = False
    if row["due_date"]:
        try:
            due = datetime.fromisoformat(
                f"{row['due_date']}T{row['due_time'] or '23:59'}"
            )
            overdue = due < datetime.now()
        except ValueError:
            pass

    return {
        "title": row["title"],
        "postpone_count": int(row["postpone_count"] or 0),
        "overdue": overdue,
    }


def task_snooze_comment(item_id: int) -> str:
    ctx = task_context(item_id)
    n = ctx["postpone_count"]
    if n <= 1:
        return "Certo. Eu volto depois. Não estou julgando ainda."
    if n == 2:
        return "Segunda adiada. Estou começando a reconhecer um padrão, mas vou fingir que não."
    if n == 3:
        return "Terceira vez. A tarefa claramente criou raízes. Eu volto de novo."
    return f"{n} adiamentos, chefe. A essa altura eu já conheço essa tarefa melhor que muita gente. Volto depois."


def task_done_comment(item_id: int) -> str:
    ctx = task_context(item_id)
    n = ctx["postpone_count"]
    if n >= 4:
        return f"Resolvido depois de {n} adiamentos. Não vou dizer 'eu avisei' porque tenho classe. Quase."
    if n == 3:
        return "Finalmente. Três adiamentos depois, a responsabilidade perdeu a guerra de desgaste."
    if n == 2:
        return "Feito. Precisou de duas prorrogações, mas eu vou contar como vitória."
    if ctx["overdue"]:
        return "Feito. Atrasado, sim. Mas morto e enterrado na lista, que é o que importa agora."
    return "Boa. Resolvido no prazo. Vou fingir que isso não me deixou discretamente satisfeito."


def routine_streak(routine_id: int) -> int:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT log_date FROM routine_logs WHERE routine_id = ? AND status = 'feito' ORDER BY log_date DESC",
            (routine_id,),
        ).fetchall()
    return _streak_from_dates([row["log_date"] for row in rows])


def routine_done_comment(routine_id: int) -> str:
    streak = routine_streak(routine_id)
    if streak >= 10:
        return f"{streak} dias seguidos. Isso já deixou de ser acidente estatístico. Continue."
    if streak >= 5:
        return f"{streak} dias seguidos. Não vou elogiar demais para não estragar, mas está funcionando."
    if streak >= 3:
        return f"{streak} dias em sequência. Olha só, constância. Quem diria."
    if streak == 2:
        return "Dois dias seguidos. Pequeno demais para comemorar, bom demais para ignorar."
    return "Registrado. Um dia não vira hábito, mas hábito nenhum começa sem esse primeiro dia."


def goal_streak(goal_id: int) -> int:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT log_date FROM goal_progress WHERE goal_id = ? ORDER BY log_date DESC",
            (goal_id,),
        ).fetchall()
    return _streak_from_dates([row["log_date"] for row in rows])


def goal_progress_comment(goal_id: int) -> str:
    streak = goal_streak(goal_id)
    if streak >= 7:
        return f"{streak} dias registrando progresso. Irritantemente consistente. Continue assim."
    if streak >= 3:
        return f"{streak} dias seguidos. Isso começa a parecer compromisso de verdade."
    return "Progresso salvo. Pouco glamour, bastante utilidade. É assim que normalmente funciona."


def workout_absence_summary() -> tuple[int, str | None]:
    with _connect() as conn:
        try:
            rows = conn.execute(
                "SELECT skip_reason FROM protocol_mass_sessions WHERE skipped_at IS NOT NULL ORDER BY skipped_at DESC"
            ).fetchall()
        except sqlite3.OperationalError:
            return 0, None
    count = len(rows)
    last_reason = rows[0]["skip_reason"] if rows else None
    return count, last_reason


def workout_skip_comment() -> str:
    count, _ = workout_absence_summary()
    if count <= 1:
        return "Falta registrada. Um dia ruim não derruba doze semanas — mas amanhã eu volto a incomodar."
    if count == 2:
        return "Segunda falta no protocolo. Ainda administrável. Só não vamos transformar exceção em calendário."
    return f"Essa é a {count}ª falta registrada no protocolo. Eu entendo que acontece; só estou guardando a conta porque alguém precisa fazer isso."


def _parse_numeric_load(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*kg\b", value.lower())
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def load_evolution_comment(exercise_name: str) -> str | None:
    with _connect() as conn:
        try:
            rows = conn.execute(
                """
                SELECT week, load
                FROM protocol_mass_set_logs
                WHERE lower(exercise_name) = lower(?) OR lower(performed_exercise) = lower(?)
                ORDER BY week, set_number
                """,
                (exercise_name, exercise_name),
            ).fetchall()
        except sqlite3.OperationalError:
            return None

    parsed = [(int(r["week"]), _parse_numeric_load(r["load"])) for r in rows]
    parsed = [(week, load) for week, load in parsed if load is not None]
    if len(parsed) < 2:
        return None

    first_week = min(week for week, _ in parsed)
    last_week = max(week for week, _ in parsed)
    if first_week == last_week:
        return None
    first = max(load for week, load in parsed if week == first_week)
    last = max(load for week, load in parsed if week == last_week)
    if first <= 0:
        return None
    pct = ((last - first) / first) * 100
    if pct >= 5:
        return f"Carga máxima registrada subiu de {first:g} kg para {last:g} kg desde a semana {first_week}. {pct:.0f}% a mais. Eu diria que estou impressionado, mas vamos manter a compostura."
    if pct <= -5:
        return f"A carga registrada caiu de {first:g} kg para {last:g} kg desde a semana {first_week}. Sem drama: vale observar recuperação, técnica e como você está chegando aos treinos."
    return f"Carga estável entre {first:g} kg e {last:g} kg desde a semana {first_week}. Nem todo progresso precisa parecer uma escada todo treino."
