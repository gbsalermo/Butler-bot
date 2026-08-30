import json
import re
from datetime import date, datetime, timedelta, timezone

import app
import language_primitives as language
import routine_integration
from settings import UTC_OFFSET_HOURS

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))


def _norm(text):
    return language.normalize_text(text)


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


async def _rows(stmt):
    result = await stmt.all()
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


def _now():
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ)


async def _uid(db, chat):
    row = await db.prepare("SELECT id FROM users WHERE telegram_chat_id=?").bind(chat).first()
    return int(_row(row, "id")) if row else None


async def _remember(db, uid, kind, iid):
    payload = json.dumps({"kind": kind, "id": iid, "detail": {}}, ensure_ascii=False)
    await db.prepare(
        "INSERT INTO natural_events(user_id,event_type,target_id,detail) VALUES(?,'context',?,?)"
    ).bind(uid, iid, payload).run()


async def remember_after_message(db, message):
    """Compatibilidade para criações que ainda terminam no `app.py` base.

    Criações naturais de lembrete, tarefa e compromisso já gravam contexto nos
    módulos autoritativos. Este hook permanece apenas para fluxos-base legados.
    """
    chat = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat:
        return

    families = set(language.detect_action_families(text))
    if not families.intersection({"reminder", "create_task", "create_appointment", "scheduled_event"}):
        return

    uid = await _uid(db, int(chat))
    if not uid:
        return
    row = await db.prepare("SELECT id,kind FROM daily_items WHERE user_id=? ORDER BY id DESC LIMIT 1").bind(uid).first()
    if row:
        await _remember(db, uid, _row(row, "kind"), int(_row(row, "id")))


async def _weekly_done(db, rid, target):
    start = target - timedelta(days=target.weekday())
    end = start + timedelta(days=6)
    row = await db.prepare(
        "SELECT COUNT(*) n FROM routine_logs WHERE routine_id=? AND log_date BETWEEN ? AND ? AND status='feito'"
    ).bind(rid, start.isoformat(), end.isoformat()).first()
    return int(_row(row, "n", 0))


def install_recurrence_patch():
    original_applies = routine_integration._applies
    original_scheduler = app.scheduled_tick

    def applies(weekdays, target):
        normalized = _norm(weekdays or "todos os dias")
        if re.search(r"\b\d+x por semana\b", normalized) or re.search(r"\ba cada \d+ dias?\b", normalized):
            return True
        return original_applies(weekdays, target)

    routine_integration._applies = applies

    async def scheduler(db, token):
        now = _now()
        today = now.date()
        clock = now.strftime("%H:%M")
        rows = await _rows(
            db.prepare(
                "SELECT r.id,r.user_id,r.time_hhmm,r.weekdays,r.created_at "
                "FROM routines r WHERE r.active=1 AND r.time_hhmm IS NOT NULL"
            )
        )
        for row in rows:
            normalized = _norm(_row(row, "weekdays") or "")
            suppress = False
            quota = re.search(r"(\d+)x por semana", normalized)
            if quota and await _weekly_done(db, int(_row(row, "id")), today) >= int(quota.group(1)):
                suppress = True
            every = re.search(r"a cada (\d+) dias?", normalized)
            if every:
                try:
                    created = date.fromisoformat((_row(row, "created_at") or "")[:10])
                    suppress = (today - created).days % int(every.group(1)) != 0
                except Exception:
                    pass
            if suppress:
                for time_hhmm in routine_integration._times(_row(row, "time_hhmm")):
                    if time_hhmm == clock:
                        key = f"routine:{_row(row,'id')}:{today.isoformat()}:{time_hhmm}"
                        await db.prepare(
                            "INSERT OR IGNORE INTO notification_log(user_id,notification_key) VALUES(?,?)"
                        ).bind(_row(row, "user_id"), key).run()
        await original_scheduler(db, token)

    app.scheduled_tick = scheduler
