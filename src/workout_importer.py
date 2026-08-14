import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from src.schedule_importer import extract_text_from_file

DAY_ALIASES = {
    "segunda": "segunda-feira", "segunda feira": "segunda-feira", "seg": "segunda-feira",
    "terca": "terça-feira", "terca feira": "terça-feira", "terça": "terça-feira", "terça feira": "terça-feira", "ter": "terça-feira",
    "quarta": "quarta-feira", "quarta feira": "quarta-feira", "qua": "quarta-feira",
    "quinta": "quinta-feira", "quinta feira": "quinta-feira", "qui": "quinta-feira",
    "sexta": "sexta-feira", "sexta feira": "sexta-feira", "sex": "sexta-feira",
    "sabado": "sábado", "sábado": "sábado", "sab": "sábado",
    "domingo": "domingo", "dom": "domingo",
}

@dataclass
class ImportedWorkoutExercise:
    weekday: str
    focus: str
    name: str
    sets: int | None
    reps: str | None
    load: str | None


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())


def _parse_day_heading(line: str) -> tuple[str | None, str | None]:
    raw = line.strip()
    normalized = _norm(raw)
    for alias, canonical in sorted(DAY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if normalized == alias:
            return canonical, None
        if normalized.startswith(alias + " "):
            rest = normalized[len(alias):].strip()
            focus = re.sub(r"^(treino|foco)\s+", "", rest).strip()
            return canonical, focus.title() if focus else None
    return None, None


def _parse_exercise(line: str) -> tuple[str, int | None, str | None, str | None] | None:
    raw = line.strip(" •-–—\t")
    if not raw:
        return None

    # Formatos preferenciais: Exercício | 4x8-10 | 40 kg  /  Exercício ; 4 x 12 ; peso corporal
    parts = [part.strip() for part in re.split(r"\s*[|;]\s*", raw) if part.strip()]
    candidate = raw
    if len(parts) >= 2:
        candidate = " ".join(parts)

    scheme = re.search(r"\b(\d{1,2})\s*[xX×]\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?|até falha|ate falha|falha)\b", candidate, flags=re.I)
    if not scheme:
        # Sem séries/repetições não gravamos automaticamente: melhor pedir um arquivo mais claro do que inventar.
        return None

    sets = int(scheme.group(1))
    reps = scheme.group(2).replace("–", "-").strip()

    before = candidate[:scheme.start()].strip(" -–—|;")
    after = candidate[scheme.end():].strip(" -–—|;")
    name = before
    if not name and parts:
        name = parts[0]
    if len(name) < 2:
        return None

    load = None
    load_match = re.search(
        r"((?:\d+(?:[.,]\d+)?\s*(?:kg|kgs|quilos?)(?:\s+cada\s+lado)?)|peso\s+corporal|sem\s+carga|el[aá]stico|halteres?|barra)",
        after,
        flags=re.I,
    )
    if load_match:
        load = load_match.group(1).strip()
    elif after:
        # Se veio num campo separado, preserva como carga/observação curta.
        load = after

    return name.strip(), sets, reps, load


def parse_workout_text(text: str) -> list[ImportedWorkoutExercise]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines()]
    lines = [line for line in lines if line]

    current_day = None
    current_focus = None
    waiting_focus = False
    exercises: list[ImportedWorkoutExercise] = []

    ignored = {"treino", "ficha de treino", "rotina de treino", "academia", "musculacao", "musculação"}

    for line in lines:
        day, focus = _parse_day_heading(line)
        if day:
            current_day = day
            current_focus = focus
            waiting_focus = focus is None
            continue

        if current_day is None:
            continue

        parsed = _parse_exercise(line)
        if parsed:
            name, sets, reps, load = parsed
            exercises.append(ImportedWorkoutExercise(
                weekday=current_day,
                focus=current_focus or "Treino",
                name=name,
                sets=sets,
                reps=reps,
                load=load,
            ))
            waiting_focus = False
            continue

        if waiting_focus and _norm(line) not in ignored and len(line) <= 60:
            current_focus = re.sub(r"^(foco|treino)\s*[:\-–—]?\s*", "", line, flags=re.I).strip() or "Treino"
            waiting_focus = False

    # Atualiza exercícios já lidos sob o mesmo dia caso o foco tenha vindo na linha seguinte ao cabeçalho.
    focus_by_day = {}
    current_day = None
    for line in lines:
        day, focus = _parse_day_heading(line)
        if day:
            current_day = day
            if focus:
                focus_by_day[day] = focus
            continue
        if current_day and current_day not in focus_by_day and not _parse_exercise(line) and len(line) <= 60 and _norm(line) not in ignored:
            focus_by_day[current_day] = re.sub(r"^(foco|treino)\s*[:\-–—]?\s*", "", line, flags=re.I).strip() or "Treino"

    for exercise in exercises:
        if exercise.weekday in focus_by_day:
            exercise.focus = focus_by_day[exercise.weekday]

    return exercises


def parse_workout_file(path: Path) -> list[ImportedWorkoutExercise]:
    return parse_workout_text(extract_text_from_file(path))
