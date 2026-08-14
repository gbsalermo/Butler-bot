import sqlite3

from src.user_scope import resolve_database_path
from src.workout_importer import ImportedWorkoutExercise


def replace_workout_plan(exercises: list[ImportedWorkoutExercise]) -> None:
    db_path = resolve_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM workout_exercises")
        conn.execute("DELETE FROM workout_days")
        day_ids: dict[str, int] = {}
        positions: dict[int, int] = {}
        for exercise in exercises:
            if exercise.weekday not in day_ids:
                cur = conn.execute("INSERT INTO workout_days (weekday, focus) VALUES (?, ?)", (exercise.weekday, exercise.focus))
                day_ids[exercise.weekday] = int(cur.lastrowid)
            day_id = day_ids[exercise.weekday]
            positions[day_id] = positions.get(day_id, 0) + 1
            conn.execute(
                "INSERT INTO workout_exercises (workout_day_id, name, load, sets, reps, position) VALUES (?, ?, ?, ?, ?, ?)",
                (day_id, exercise.name, exercise.load, exercise.sets, exercise.reps, positions[day_id]),
            )
