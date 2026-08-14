import sqlite3
from datetime import date, datetime, timedelta

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from src.daily_store import list_item_history
from src.user_scope import resolve_database_path

HISTORY_DATE = 900

WEEKDAYS = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

HISTORY_MENU = ReplyKeyboardMarkup(
    [["📖 Histórico diário", "🗂️ Histórico de tarefas"], ["🏠 Menu principal"]],
    resize_keyboard=True,
)
CANCEL_KEYBOARD = ReplyKeyboardMarkup([["❌ Cancelar ação"]], resize_keyboard=True)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(resolve_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def _parse_history_date(text: str) -> date | None:
    value = text.strip().lower()
    if value in {"hoje"}:
        return date.today()
    if value in {"ontem"}:
        return date.today() - timedelta(days=1)
    for fmt in ("%d/%m/%Y", "%d/%m"):
        try:
            parsed = datetime.strptime(text.strip(), fmt)
            year = parsed.year if fmt == "%d/%m/%Y" else date.today().year
            return date(year, parsed.month, parsed.day)
        except ValueError:
            continue
    return None


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


def _routine_logs_for(target: date) -> list[sqlite3.Row]:
    with _connect() as conn:
        try:
            return conn.execute(
                """
                SELECT r.name, rl.status
                FROM routine_logs rl
                JOIN routines r ON r.id = rl.routine_id
                WHERE rl.log_date = ?
                ORDER BY r.name
                """,
                (target.isoformat(),),
            ).fetchall()
        except sqlite3.OperationalError:
            return []


def _workout_for(target: date) -> str | None:
    with _connect() as conn:
        try:
            session = conn.execute(
                """
                SELECT week, weekday, completed_at, skipped_at, skip_reason
                FROM protocol_mass_sessions
                WHERE training_date = ?
                ORDER BY id DESC LIMIT 1
                """,
                (target.isoformat(),),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    if not session:
        return None
    if session["completed_at"]:
        return f"✅ Treino na academia concluído — semana {session['week']}"
    if session["skipped_at"]:
        reason = f" — motivo: {session['skip_reason']}" if session["skip_reason"] else ""
        return f"➖ Treino na academia não realizado{reason}"
    return "⬜ Treino na academia iniciado, sem conclusão registrada"


def _status_label(row: sqlite3.Row) -> str:
    status = row["status"]
    if status == "concluido":
        return "✅ concluída" if row["kind"] == "tarefa" else "✅ concluído"
    if status == "cancelado":
        return "🚫 cancelada" if row["kind"] == "tarefa" else "🚫 cancelado"
    return "⏳ pendente"


def build_day_history(target: date) -> str:
    weekday = WEEKDAYS[target.weekday()]
    classes = _classes_for(target)
    items = _items_for(target)
    routines = _routine_logs_for(target)
    workout = _workout_for(target)

    parts = [f"📖 *Histórico — {weekday.capitalize()}, {target.strftime('%d/%m/%Y')}*"]

    if classes:
        parts.append("\n🎓 *Aulas previstas*")
        for row in classes:
            parts.append(
                f"• {row['start_time']} — {row['name']} ({row['location'] or 'local não informado'})"
            )

    tasks = [r for r in items if r["kind"] == "tarefa"]
    appointments = [r for r in items if r["kind"] == "compromisso"]
    if tasks:
        parts.append("\n✅ *Tarefas*")
        for row in tasks:
            when = f"{row['due_time']} — " if row["due_time"] else ""
            parts.append(f"• {when}{row['title']} — {_status_label(row)}")
    if appointments:
        parts.append("\n📅 *Compromissos*")
        for row in appointments:
            when = f"{row['due_time']} — " if row["due_time"] else ""
            parts.append(f"• {when}{row['title']} — {_status_label(row)}")

    if routines:
        parts.append("\n🧘 *Rotinas registradas*")
        for row in routines:
            icon = "✅" if row["status"] == "feito" else "•"
            parts.append(f"• {icon} {row['name']}")

    if workout:
        parts.append(f"\n🏋️ *Academia*\n• {workout}")

    if not any((classes, tasks, appointments, routines, workout)):
        parts.append("\nNão encontrei registros para esse dia. Ou foi tranquilo, ou o Butler ainda não estava tomando conta da papelada. 👀")
    else:
        parts.append("\n_Esse histórico mostra o que foi registrado no Butler; aula prevista não significa presença confirmada._")

    return "\n".join(parts)


async def history_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📚 *Histórico*\n\nQuer reconstruir um dia específico ou conferir a situação das tarefas?",
        parse_mode="Markdown",
        reply_markup=HISTORY_MENU,
    )


async def day_history_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📖 Qual dia quer conferir?\n\nUse `ontem`, `hoje`, `DD/MM` ou `DD/MM/AAAA`.",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD,
    )
    return HISTORY_DATE


async def day_history_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text == "❌ Cancelar ação":
        await update.message.reply_text("Consulta cancelada.", reply_markup=HISTORY_MENU)
        return ConversationHandler.END
    target = _parse_history_date(text)
    if target is None:
        await update.message.reply_text("Não reconheci a data. Use `ontem`, `hoje`, `DD/MM` ou `DD/MM/AAAA`.", parse_mode="Markdown")
        return HISTORY_DATE
    await update.message.reply_text(build_day_history(target), parse_mode="Markdown", reply_markup=HISTORY_MENU)
    return ConversationHandler.END


async def task_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = list_item_history(kind="tarefa")
    pending = [r for r in rows if r["status"] == "pendente"]
    done = [r for r in rows if r["status"] == "concluido"]
    cancelled = [r for r in rows if r["status"] == "cancelado"]

    parts = ["🗂️ *Histórico de tarefas*"]
    sections = [
        ("⏳ Pendentes", pending),
        ("✅ Concluídas", done),
        ("🚫 Canceladas", cancelled),
    ]
    for title, group in sections:
        parts.append(f"\n*{title} — {len(group)}*")
        if not group:
            parts.append("• nenhuma")
            continue
        for row in group[-10:]:
            due = ""
            if row["due_date"]:
                due = " — " + datetime.fromisoformat(row["due_date"]).strftime("%d/%m/%Y")
            if row["due_time"]:
                due += f" às {row['due_time']}"
            parts.append(f"• #{row['id']} {row['title']}{due}")
        if len(group) > 10:
            parts.append(f"• ...e mais {len(group) - 10}")

    parts.append("\n_Itens removidos antes desta versão não podem ser recuperados; daqui para frente, remover arquiva como cancelado._")
    await update.message.reply_text("\n".join(parts), parse_mode="Markdown", reply_markup=HISTORY_MENU)


def register_history_handlers(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(r"^📚 Histórico$"), history_menu), group=-4)
    application.add_handler(MessageHandler(filters.Regex(r"^🗂️ Histórico de tarefas$"), task_history), group=-4)
    application.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(r"^📖 Histórico diário$"), day_history_start)],
            states={HISTORY_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, day_history_receive)]},
            fallbacks=[],
        ),
        group=-4,
    )
