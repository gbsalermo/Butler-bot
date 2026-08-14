import sqlite3
from datetime import date, datetime, timedelta

from src.behavior_engine import routine_streak
from src.home_store import list_missing_groceries, list_workout
from src.user_scope import resolve_database_path

WEEKDAYS = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(resolve_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def _classes_for(target: date) -> list[sqlite3.Row]:
    weekday = WEEKDAYS[target.weekday()]
    with _connect() as conn:
        try:
            return conn.execute(
                """
                SELECT s.name, cs.start_time, cs.end_time, cs.location
                FROM class_sessions cs
                JOIN subjects s ON s.id = cs.subject_id
                WHERE s.active = 1 AND cs.weekday = ?
                ORDER BY cs.start_time, s.name
                """,
                (weekday,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []


def _items_for(target: date) -> list[sqlite3.Row]:
    with _connect() as conn:
        try:
            return conn.execute(
                """
                SELECT * FROM daily_items
                WHERE due_date = ?
                ORDER BY CASE WHEN due_time IS NULL THEN 1 ELSE 0 END, due_time, id
                """,
                (target.isoformat(),),
            ).fetchall()
        except sqlite3.OperationalError:
            return []


def _overdue_tasks(before: date) -> list[sqlite3.Row]:
    with _connect() as conn:
        try:
            return conn.execute(
                """
                SELECT * FROM daily_items
                WHERE kind = 'tarefa' AND status = 'pendente'
                  AND due_date IS NOT NULL AND due_date < ?
                ORDER BY due_date, due_time, id
                """,
                (before.isoformat(),),
            ).fetchall()
        except sqlite3.OperationalError:
            return []


def _routine_stats(target: date) -> tuple[int, int, str | None]:
    with _connect() as conn:
        try:
            routines = conn.execute("SELECT id, name FROM routines WHERE active = 1").fetchall()
            completed = conn.execute(
                "SELECT COUNT(DISTINCT routine_id) FROM routine_logs WHERE log_date = ? AND status = 'feito'",
                (target.isoformat(),),
            ).fetchone()[0]
        except sqlite3.OperationalError:
            return 0, 0, None

    best_name = None
    best_streak = 0
    for routine in routines:
        streak = routine_streak(int(routine["id"]))
        if streak > best_streak:
            best_streak = streak
            best_name = str(routine["name"])
    highlight = f"{best_name}: {best_streak} dias seguidos" if best_name and best_streak >= 2 else None
    return int(completed), len(routines), highlight


def _workout_for(target: date) -> str | None:
    weekday = WEEKDAYS[target.weekday()]
    rows = [row for row in list_workout() if row["weekday"] == weekday]
    if not rows:
        return None
    return str(rows[0]["focus"])


def _protocol_table_exists() -> bool:
    with _connect() as conn:
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='protocol_mass_state'"
            ).fetchone()
            return row is not None
        except sqlite3.OperationalError:
            return False


def _protocol_today(target: date) -> tuple[str | None, str | None]:
    weekday = WEEKDAYS[target.weekday()]
    with _connect() as conn:
        try:
            state = conn.execute("SELECT * FROM protocol_mass_state WHERE id = 1").fetchone()
            # O treino pessoal só existe para os resumos depois de
            # 'Começar os trabalhos'. Antes disso, silêncio total sobre academia.
            if not state or not state["active"]:
                return None, None
            session = conn.execute(
                """
                SELECT completed_at, skipped_at, skip_reason
                FROM protocol_mass_sessions
                WHERE week = ? AND weekday = ?
                """,
                (int(state["current_week"]), weekday),
            ).fetchone()
        except sqlite3.OperationalError:
            return None, None

    label = "treino na academia"
    if session and session["completed_at"]:
        return label, "concluido"
    if session and session["skipped_at"]:
        return label, "faltou"
    if weekday != "domingo":
        return label, "pendente"
    return None, None


def _summary_workout(target: date) -> str | None:
    """Resolve o treino mostrado nos resumos.

    Butler pessoal: se a tabela do protocolo existe, treino só aparece quando
    o protocolo estiver ativo após 'Começar os trabalhos'.
    Butler genérico: sem Protocol Mass, pode usar a rotina manual de musculação.
    """
    if _protocol_table_exists():
        protocol, _ = _protocol_today(target)
        return protocol
    return _workout_for(target)


def morning_summary(name: str, target: date | None = None) -> str:
    target = target or date.today()
    classes = _classes_for(target)
    items = _items_for(target)
    tasks = [row for row in items if row["kind"] == "tarefa" and row["status"] == "pendente"]
    appointments = [row for row in items if row["kind"] == "compromisso" and row["status"] == "pendente"]
    overdue = _overdue_tasks(target)
    groceries = list_missing_groceries()
    workout = _summary_workout(target)

    chunks = []
    if classes:
        chunks.append(f"{len(classes)} aula{'s' if len(classes) != 1 else ''}")
    if tasks:
        chunks.append(f"{len(tasks)} tarefa{'s' if len(tasks) != 1 else ''}")
    if appointments:
        chunks.append(f"{len(appointments)} compromisso{'s' if len(appointments) != 1 else ''}")
    if workout:
        chunks.append(workout)

    if chunks:
        opening = f"Bom dia, {name}. Hoje temos " + ", ".join(chunks[:-1]) + (f" e {chunks[-1]}" if len(chunks) > 1 else chunks[0]) + "."
    else:
        opening = f"Bom dia, {name}. O calendário está estranhamente civilizado hoje. Aproveite antes que ele mude de ideia."

    parts = [f"☀️ *Resumo da manhã*\n\n{opening}"]
    if classes:
        parts.append("\n🎓 *Aulas*")
        for row in classes:
            parts.append(f"• {row['start_time']} — {row['name']} ({row['location'] or 'local não informado'})")
    if tasks or appointments:
        parts.append("\n📋 *Agenda*")
        for row in items:
            if row["status"] != "pendente":
                continue
            icon = "✅" if row["kind"] == "tarefa" else "📅"
            when = f"{row['due_time']} — " if row["due_time"] else ""
            parts.append(f"• {icon} {when}{row['title']}")
    if workout:
        parts.append("\n🏋️ *Treino na academia previsto hoje.*")
    if overdue:
        parts.append(f"\n📌 E existem *{len(overdue)} tarefa(s) atrasada(s)* me encarando no banco. Estou repassando o olhar.")
    if groceries:
        sample = ", ".join(str(row["name"]) for row in groceries[:3])
        suffix = "..." if len(groceries) > 3 else ""
        parts.append(f"\n🛒 Faltando em casa: {sample}{suffix}")

    parts.append("\nNada demais. Só a administração básica de uma pequena empresa chamada sua vida. 😌")
    return "\n".join(parts)


def nightly_summary(name: str, target: date | None = None) -> str:
    target = target or date.today()
    items = _items_for(target)
    tasks = [row for row in items if row["kind"] == "tarefa"]
    appointments = [row for row in items if row["kind"] == "compromisso"]
    done_tasks = [row for row in tasks if row["status"] == "concluido"]
    pending_tasks = [row for row in tasks if row["status"] == "pendente"]
    completed_routines, total_routines, streak = _routine_stats(target)
    protocol, protocol_status = _protocol_today(target)

    parts = [f"🌙 *Fechamento do dia*\n\n{name}, vamos aos números antes que alguém tente reescrever a história:"]
    if tasks:
        parts.append(f"• ✅ Tarefas: *{len(done_tasks)}/{len(tasks)} concluídas*")
    if appointments:
        parts.append(f"• 📅 Compromissos previstos: *{len(appointments)}*")
    if total_routines:
        parts.append(f"• 🧘 Rotinas registradas hoje: *{completed_routines}/{total_routines}*")
    if protocol:
        labels = {"concluido": "✅ concluído", "faltou": "➖ falta registrada", "pendente": "⬜ sem conclusão registrada"}
        parts.append(f"• 🏋️ Treino na academia: {labels.get(protocol_status, protocol_status)}")

    if pending_tasks:
        parts.append("\n📌 *Ficou para trás:*")
        for row in pending_tasks[:5]:
            parts.append(f"• {row['title']}")
        if len(pending_tasks) > 5:
            parts.append(f"• ...e mais {len(pending_tasks) - 5}. Sim, eu contei.")
    elif tasks:
        parts.append("\n😏 Nenhuma tarefa de hoje ficou aberta. Não vou fazer festa, mas notei.")

    if streak:
        parts.append(f"\n🔥 Melhor sequência ativa: *{streak}*.")

    if pending_tasks:
        parts.append("\nAmanhã a gente resolve o restante. 'A gente', no caso, significa eu lembrando e você fazendo. A divisão parece justa.")
    else:
        parts.append("\nDia fechado. Pode descansar com a rara satisfação administrativa de não ter deixado tudo pegar fogo. 😌")
    return "\n".join(parts)


def weekly_summary(name: str, end: date | None = None) -> str:
    end = end or date.today()
    start = end - timedelta(days=6)
    with _connect() as conn:
        try:
            items = conn.execute(
                """
                SELECT * FROM daily_items
                WHERE due_date BETWEEN ? AND ?
                """,
                (start.isoformat(), end.isoformat()),
            ).fetchall()
            routine_done = conn.execute(
                """
                SELECT COUNT(*) FROM routine_logs
                WHERE log_date BETWEEN ? AND ? AND status = 'feito'
                """,
                (start.isoformat(), end.isoformat()),
            ).fetchone()[0]
        except sqlite3.OperationalError:
            items = []
            routine_done = 0

    tasks = [r for r in items if r["kind"] == "tarefa"]
    done_tasks = [r for r in tasks if r["status"] == "concluido"]
    appointments = [r for r in items if r["kind"] == "compromisso"]
    overdue_now = _overdue_tasks(end + timedelta(days=1))

    parts = [
        "📊 *Fechamento semanal*",
        f"\n{name}, balanço de {start.strftime('%d/%m')} a {end.strftime('%d/%m')}. Vou tentar não parecer orgulhoso demais.",
        f"\n• ✅ Tarefas concluídas: *{len(done_tasks)}/{len(tasks)}*",
        f"• 📅 Compromissos registrados: *{len(appointments)}*",
        f"• 🧘 Rotinas cumpridas: *{int(routine_done)} registros*",
    ]

    with _connect() as conn:
        try:
            state = conn.execute("SELECT * FROM protocol_mass_state WHERE id = 1").fetchone()
            # Antes de 'Começar os trabalhos', musculação não entra no balanço.
            if state and state["active"]:
                week = int(state["current_week"])
                sessions = conn.execute(
                    "SELECT completed_at, skipped_at FROM protocol_mass_sessions WHERE week = ?",
                    (week,),
                ).fetchall()
                done = sum(1 for r in sessions if r["completed_at"])
                skipped = sum(1 for r in sessions if r["skipped_at"])
                parts.append(f"• 🏋️ Treino na academia — semana {week}: *{done} treino(s) concluído(s)*, *{skipped} falta(s)*")
        except sqlite3.OperationalError:
            pass

    if overdue_now:
        parts.append(f"\n👀 Ainda existem *{len(overdue_now)} tarefa(s) vencida(s)* abertas. A semana acabou; elas, inconvenientemente, não.")
    elif tasks:
        parts.append("\n✅ Nenhuma tarefa vencida aberta agora. Estranhamente competente da sua parte.")

    _, _, streak = _routine_stats(end)
    if streak:
        parts.append(f"\n🔥 Destaque de constância: *{streak}*.")

    completion = (len(done_tasks) / len(tasks) * 100) if tasks else 100
    if tasks and completion >= 80:
        parts.append("\nBoa semana. Eu diria que você mandou bem, mas não quero criar expectativas emocionais entre nós. 😏")
    elif tasks and completion < 50:
        parts.append("\nSemana meio torta. Nada irreversível — mas na próxima eu vou precisar incomodar com um pouco mais de convicção. 👀")
    else:
        parts.append("\nSemana encerrada. Houve progresso, houve bagunça, sobrevivemos. Um resultado tecnicamente aceitável. 😌")
    return "\n".join(parts)
