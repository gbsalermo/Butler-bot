import sqlite3
import unicodedata
from datetime import date, timedelta

from src.user_scope import resolve_database_path

TRACKED_CATEGORIES = {
    "ingles": ("🇬🇧", "Inglês"),
    "programacao": ("💻", "Programação"),
    "agua": ("💧", "Água"),
    "alimentacao": ("🥗", "Alimentação"),
    "musculacao": ("🏋️", "Musculação"),
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(resolve_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", (value or "").lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch)).strip()


def _current_streak(days: set[date]) -> int:
    if not days:
        return 0
    today = date.today()
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _best_streak(days: set[date]) -> int:
    if not days:
        return 0
    ordered = sorted(days)
    best = current = 1
    for previous, current_day in zip(ordered, ordered[1:]):
        if current_day == previous + timedelta(days=1):
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


def _goal_days(category: str) -> set[date]:
    with _connect() as conn:
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT gp.log_date
                FROM goal_progress gp
                JOIN goals g ON g.id = gp.goal_id
                WHERE g.active = 1
                """
            ).fetchall()
        except sqlite3.OperationalError:
            return set()
        goal_rows = conn.execute("SELECT id, category FROM goals WHERE active = 1").fetchall()
        ids = {int(r['id']) for r in goal_rows if _normalize(r['category']) == category}
        if not ids:
            return set()
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT DISTINCT log_date FROM goal_progress WHERE goal_id IN ({placeholders})",
            tuple(ids),
        ).fetchall()
    return {date.fromisoformat(r["log_date"]) for r in rows if r["log_date"]}


def _routine_days(category: str) -> set[date]:
    with _connect() as conn:
        try:
            routines = conn.execute("SELECT id, category FROM routines WHERE active = 1").fetchall()
        except sqlite3.OperationalError:
            return set()
        ids = {int(r['id']) for r in routines if _normalize(r['category']) == category}
        if not ids:
            return set()
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT DISTINCT log_date FROM routine_logs WHERE status = 'feito' AND routine_id IN ({placeholders})",
            tuple(ids),
        ).fetchall()
    return {date.fromisoformat(r["log_date"]) for r in rows if r["log_date"]}


def _workout_days() -> set[date]:
    with _connect() as conn:
        try:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='protocol_mass_sessions'"
            ).fetchone()
            if not exists:
                return set()
            rows = conn.execute(
                "SELECT DISTINCT training_date FROM protocol_mass_sessions WHERE completed_at IS NOT NULL"
            ).fetchall()
        except sqlite3.OperationalError:
            return set()
    return {date.fromisoformat(r["training_date"]) for r in rows if r["training_date"]}


def category_days(category: str) -> set[date]:
    normalized = _normalize(category)
    if normalized == "musculacao":
        workout = _workout_days()
        if workout:
            return workout
    return _goal_days(normalized) | _routine_days(normalized)


def streak_snapshot(category: str) -> dict:
    days = category_days(category)
    return {
        "current": _current_streak(days),
        "best": _best_streak(days),
        "total_days": len(days),
        "days": days,
    }


def _last_seven_marks(days: set[date]) -> str:
    marks = []
    for offset in range(6, -1, -1):
        target = date.today() - timedelta(days=offset)
        marks.append("🟩" if target in days else "⬜")
    return "".join(marks)


def streak_dashboard() -> str:
    parts = ["🔥 *Sequências*", "", "Um pouco de pressão visual. Porque aparentemente funciona."]
    any_data = False
    for key, (icon, label) in TRACKED_CATEGORIES.items():
        snap = streak_snapshot(key)
        if snap["total_days"]:
            any_data = True
        fire = "🔥" if snap["current"] >= 3 else ""
        parts.append(
            f"\n{icon} *{label}*\n"
            f"{_last_seven_marks(snap['days'])}\n"
            f"Atual: *{snap['current']}* dia(s) {fire} • Recorde: *{snap['best']}* • Total: *{snap['total_days']}*"
        )

    if not any_data:
        parts.append("\nAinda não há registros suficientes. A parte chata é que a sequência precisa começar no dia 1. 😌")
    else:
        best = max((streak_snapshot(k)["current"], label) for k, (_, label) in TRACKED_CATEGORIES.items())
        if best[0] >= 7:
            parts.append(f"\n😏 {best[1]} está em *{best[0]} dias*. Isso já está começando a parecer disciplina. Cuidado.")
        elif best[0] >= 3:
            parts.append(f"\n👀 Melhor sequência atual: *{best[1]} — {best[0]} dias*. Não pare agora só para me contrariar.")
        else:
            parts.append("\nTem movimento. Ainda é cedo para discurso motivacional, graças a Deus.")
    return "\n".join(parts)
