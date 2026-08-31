"""Relógio persistente de contingência para notificações pessoais.

O Cron Trigger continua sendo o scheduler primário, mas este Durable Object
mantém um próximo evento armado por usuário. Ele cobre:

- tarefas com horário;
- compromissos (T-5);
- lembretes pessoais;
- timers/alertas rápidos;
- checkpoints de rotina;
- resumo da manhã;
- fechamento semanal.

O objetivo é eliminar o Cron Trigger como ponto único de falha. O estado de
entrega continua idempotente em ``notification_log`` e os dispatchers finais
continuam sendo as autoridades das regras de negócio.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from workers import DurableObject, Response

from day_off_policy import expire_stale_day_offs
from quick_time import dispatch_due_quick_timers, next_quick_timer
from reliable_reminders import dispatch_due_reminders
from reliable_summaries import dispatch_summaries
from routine_integration import _applies, _routine_reminders, _times
from settings import (
    MORNING_SUMMARY_HOUR,
    MORNING_SUMMARY_MINUTE,
    UTC_OFFSET_HOURS,
    WEEKLY_SUMMARY_HOUR,
    WEEKLY_SUMMARY_MINUTE,
    WEEKLY_SUMMARY_WEEKDAY,
)

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
STRICT_REMINDER_DELAY_MINUTES = 2
APPOINTMENT_GRACE_MINUTES = 10
ROUTINE_GRACE_MINUTES = 2
MORNING_RECOVERY_MINUTES = 300
WEEKLY_GRACE_MINUTES = 60


def _row(row, key, default=None):
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


async def _sent(db, uid, key):
    row = await db.prepare(
        "SELECT id FROM notification_log WHERE user_id=? AND notification_key=?"
    ).bind(uid, key).first()
    return bool(row)


def _at(day, time_text):
    h, m = map(int, time_text.split(":"))
    return datetime.combine(day, datetime.min.time()).replace(
        hour=h,
        minute=m,
        tzinfo=LOCAL_TZ,
    )


def _item_desired(item):
    """Retorna (instante do aviso, tipo lógico) conforme reliable_reminders."""
    details = _row(item, "details") or ""
    if details.startswith("exam:"):
        return None

    try:
        day = datetime.strptime(_row(item, "due_date"), "%Y-%m-%d").date()
        due = _at(day, _row(item, "due_time"))
    except Exception:
        return None

    kind = _row(item, "kind")
    simple = details == "simple_reminder"
    advance = 5 if kind == "compromisso" and not simple else 0
    desired = due - timedelta(minutes=advance)
    logical_kind = "lembrete" if simple else kind
    return desired, logical_kind


def _recoverable_candidate(now, desired, logical_kind):
    """Replica as janelas úteis sem transformar aviso velho em spam."""
    if desired > now:
        return desired

    late = now - desired
    if logical_kind == "tarefa":
        if desired.date() == now.date():
            return now + timedelta(seconds=1)
        return None
    if logical_kind == "lembrete":
        if late <= timedelta(minutes=STRICT_REMINDER_DELAY_MINUTES):
            return now + timedelta(seconds=1)
        return None
    if logical_kind == "compromisso":
        if late <= timedelta(minutes=APPOINTMENT_GRACE_MINUTES):
            return now + timedelta(seconds=1)
        return None
    return None


async def _item_candidates(db, uid, now, day_off):
    candidates = []
    today = now.date()
    items = await _rows(
        db.prepare(
            "SELECT id,kind,due_date,due_time,details,status FROM daily_items "
            "WHERE user_id=? AND status='pendente' AND due_time IS NOT NULL "
            "AND due_date>=? ORDER BY due_date,due_time LIMIT 200"
        ).bind(uid, today.isoformat())
    )

    for item in items:
        parsed = _item_desired(item)
        if parsed is None:
            continue
        desired, logical_kind = parsed
        if day_off and desired.date() == today and logical_kind != "lembrete":
            continue

        iid = int(_row(item, "id"))
        key = f"item:new:{iid}:{today if desired.date() == today else desired.date()}:{desired.strftime('%H:%M')}"
        if await _sent(db, uid, key):
            continue

        candidate = _recoverable_candidate(now, desired, logical_kind)
        if candidate is not None:
            candidates.append(candidate)

    return candidates


async def _routine_candidates(db, uid, now, day_off):
    candidates = []
    today = now.date()
    routines = await _rows(
        db.prepare(
            "SELECT id,name,time_hhmm,weekdays FROM routines "
            "WHERE user_id=? AND active=1 AND time_hhmm IS NOT NULL"
        ).bind(uid)
    )

    for offset in range(0, 8):
        day = today + timedelta(days=offset)
        for routine in routines:
            if not _applies(_row(routine, "weekdays"), day):
                continue
            if day_off and day == today:
                continue

            rid = int(_row(routine, "id"))
            for time_text in _times(_row(routine, "time_hhmm")):
                try:
                    desired = _at(day, time_text)
                except Exception:
                    continue
                key = f"routine:{rid}:{day.isoformat()}:{time_text}"
                if await _sent(db, uid, key):
                    continue
                if desired > now:
                    candidates.append(desired)
                elif day == today and now - desired <= timedelta(minutes=ROUTINE_GRACE_MINUTES):
                    candidates.append(now + timedelta(seconds=1))

    return candidates


async def _summary_candidates(db, uid, now, day_off):
    candidates = []
    today = now.date()

    morning_key = f"morning:{today.isoformat()}"
    morning_sent = await _sent(db, uid, morning_key)
    morning = now.replace(
        hour=MORNING_SUMMARY_HOUR,
        minute=MORNING_SUMMARY_MINUTE,
        second=0,
        microsecond=0,
    )
    morning_end = morning + timedelta(minutes=MORNING_RECOVERY_MINUTES)

    if not day_off and not morning_sent:
        if now < morning:
            candidates.append(morning)
        elif now <= morning_end:
            candidates.append(now + timedelta(seconds=1))

    tomorrow_morning = morning + timedelta(days=1)
    candidates.append(tomorrow_morning)

    if today.weekday() == WEEKLY_SUMMARY_WEEKDAY:
        weekly_key = f"weekly:{today.isoformat()}"
        weekly_sent = await _sent(db, uid, weekly_key)
        weekly = now.replace(
            hour=WEEKLY_SUMMARY_HOUR,
            minute=WEEKLY_SUMMARY_MINUTE,
            second=0,
            microsecond=0,
        )
        weekly_end = weekly + timedelta(minutes=WEEKLY_GRACE_MINUTES)
        if not day_off and not weekly_sent:
            if now < weekly:
                candidates.append(weekly)
            elif now <= weekly_end:
                candidates.append(now + timedelta(seconds=1))

    return candidates


async def _next_event(db, uid, now=None):
    now = now or datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    state = await db.prepare(
        "SELECT COALESCE(day_off,0) day_off FROM assistant_state WHERE user_id=?"
    ).bind(uid).first()
    day_off = bool(int(_row(state, "day_off", 0) or 0))

    candidates = []
    candidates.extend(await _item_candidates(db, uid, now, day_off))
    candidates.extend(await _routine_candidates(db, uid, now, day_off))
    candidates.extend(await _summary_candidates(db, uid, now, day_off))

    # Timers rápidos ignoram Day-off: um cronômetro de cozinha ou alerta pontual
    # continua sendo uma instrução explícita e temporária do usuário.
    quick = await next_quick_timer(db, uid, now=now.astimezone(timezone.utc))
    if quick is not None:
        candidates.append(quick)

    return min(candidates) if candidates else None


class PersonalAlarm(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.storage = ctx.storage
        self.env = env

    async def fetch(self, request):
        raw = (parse_qs(urlparse(request.url).query).get("user_id") or [None])[0]
        if raw is None:
            return Response("missing user_id", status=400)
        try:
            uid = int(raw)
        except Exception:
            return Response("invalid user_id", status=400)

        await self.storage.put("user_id", uid)
        await self._schedule(uid)
        return Response("ok")

    async def _schedule(self, uid):
        when = await _next_event(self.env.DB, uid)
        if when is None:
            try:
                self.storage.deleteAlarm()
            except Exception:
                pass
            return
        self.storage.setAlarm(int(when.timestamp() * 1000))

    async def alarm(self, alarm_info=None):
        uid = await self.storage.get("user_id")
        if uid is None:
            return
        uid = int(uid)

        await expire_stale_day_offs(self.env.DB)

        # Todos os dispatchers são idempotentes. Quick timers usam status próprio
        # + notification_log; os demais preservam suas políticas existentes.
        await dispatch_due_quick_timers(
            self.env.DB,
            self.env.TELEGRAM_BOT_TOKEN,
            user_id=uid,
        )
        await dispatch_due_reminders(self.env.DB, self.env.TELEGRAM_BOT_TOKEN)
        await _routine_reminders(self.env.DB, self.env.TELEGRAM_BOT_TOKEN)
        await dispatch_summaries(self.env.DB, self.env.TELEGRAM_BOT_TOKEN)
        await self._schedule(uid)


async def sync_personal_alarms(env):
    """Garante um relógio persistente por usuário, sem depender do próximo cron."""
    users = await _rows(env.DB.prepare("SELECT id FROM users"))
    for row in users:
        try:
            uid = int(_row(row, "id"))
            stub = env.PERSONAL_ALARMS.getByName(str(uid))
            await stub.fetch(f"https://personal-alarm/sync?user_id={uid}")
        except Exception as exc:
            print(
                f"[personal-alarm-sync] user_id={_row(row,'id')} "
                f"type={type(exc).__name__} message={str(exc)[:300]}"
            )
