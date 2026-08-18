"""Agendamento persistente dos avisos de aula com Durable Object Alarms.

O Cron continua sincronizando a agenda como redundância, mas os eventos T-10 e T0
ficam persistidos no Durable Object de cada usuário. Assim um minuto perdido pelo
Cron não elimina o aviso.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from workers import DurableObject, Response

import app
import attendance_patch as attendance
from attendance_production_fix import dispatch_class_attendance_reliable
from settings import UTC_OFFSET_HOURS

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
PRE_CLASS_MINUTES = 10


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


def _bounds(day, start_text, end_text):
    sh, sm = map(int, start_text.split(":"))
    start = datetime.combine(day, datetime.min.time()).replace(
        hour=sh, minute=sm, tzinfo=LOCAL_TZ
    )
    try:
        eh, em = map(int, (end_text or "").split(":"))
        end = datetime.combine(day, datetime.min.time()).replace(
            hour=eh, minute=em, tzinfo=LOCAL_TZ
        )
        if end <= start:
            end += timedelta(days=1)
    except Exception:
        end = start + timedelta(hours=1)
    return start, end


async def _next_event(db, uid, now=None):
    now = now or datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    sessions = await _rows(db.prepare("""
        SELECT ss.id,ss.weekday,ss.start_time,ss.end_time,s.name
        FROM subject_sessions ss
        JOIN subjects s ON s.id=ss.subject_id
        WHERE s.user_id=? AND s.active=1 AND ss.start_time IS NOT NULL
        ORDER BY ss.weekday,ss.start_time
    """).bind(uid))
    if not sessions:
        return None

    candidates = []
    today = now.date()
    for session in sessions:
        sid = int(_row(session, "id"))
        weekday = _row(session, "weekday")
        try:
            weekday_idx = app.WEEKDAY_NAMES.index(weekday)
        except Exception:
            continue

        # Hoje + próximos 7 dias cobre a próxima ocorrência mesmo quando a sessão
        # desta semana já passou.
        for offset in range(0, 8):
            day = today + timedelta(days=offset)
            if day.weekday() != weekday_idx:
                continue
            try:
                start, end = _bounds(day, _row(session, "start_time"), _row(session, "end_time"))
            except Exception:
                continue

            date_key = day.isoformat()
            pre_key = f"attendance:pre:{date_key}:{sid}"
            start_key = f"attendance:start:{date_key}:{sid}"
            legacy_key = f"attendance:{date_key}:{sid}"
            pre = start - timedelta(minutes=PRE_CLASS_MINUTES)

            # Se o sincronizador acordar dentro da janela pré-aula e o pré-aviso
            # ainda não tiver saído, arma um alarm imediato.
            if pre <= now < start and not await _sent(db, uid, pre_key):
                candidates.append((now + timedelta(seconds=1), "pre", sid, day))
            elif pre > now and not await _sent(db, uid, pre_key):
                candidates.append((pre, "pre", sid, day))

            # Início pode ser recuperado enquanto a aula estiver acontecendo.
            start_sent = await _sent(db, uid, start_key) or await _sent(db, uid, legacy_key)
            if start <= now < end and not start_sent:
                candidates.append((now + timedelta(seconds=1), "start", sid, day))
            elif start > now and not start_sent:
                candidates.append((start, "start", sid, day))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0]


class AttendanceAlarm(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.storage = ctx.storage
        self.env = env

    async def fetch(self, request):
        parsed = urlparse(request.url)
        params = parse_qs(parsed.query)
        raw_uid = (params.get("user_id") or [None])[0]
        if raw_uid is None:
            return Response("missing user_id", status=400)
        try:
            uid = int(raw_uid)
        except Exception:
            return Response("invalid user_id", status=400)

        await self.storage.put("user_id", uid)
        await self._schedule_next(uid)
        return Response("ok")

    async def _schedule_next(self, uid):
        event = await _next_event(self.env.DB, uid)
        if event is None:
            try:
                self.storage.deleteAlarm()
            except Exception:
                pass
            return

        when, phase, sid, day = event
        await self.storage.put("next_phase", phase)
        await self.storage.put("next_session_id", sid)
        await self.storage.put("next_date", day.isoformat())
        # setAlarm usa epoch em milissegundos.
        self.storage.setAlarm(int(when.timestamp() * 1000))

    async def alarm(self, alarm_info=None):
        uid = await self.storage.get("user_id")
        if uid is None:
            return
        uid = int(uid)

        # strict=True faz falha de Telegram/D1 escapar do handler. Durable Object
        # Alarms então aplica retry automático; não marcamos envio sem confirmação.
        await dispatch_class_attendance_reliable(
            self.env.DB,
            self.env.TELEGRAM_BOT_TOKEN,
            user_id=uid,
            strict=True,
            heartbeat=False,
        )
        await self._schedule_next(uid)


async def sync_attendance_alarms(env):
    """Garante um alarm persistente por usuário que possui alguma aula ativa."""
    users = await _rows(env.DB.prepare("""
        SELECT DISTINCT u.id
        FROM users u
        JOIN subjects s ON s.user_id=u.id AND s.active=1
        JOIN subject_sessions ss ON ss.subject_id=s.id
        WHERE ss.start_time IS NOT NULL
    """))
    for row in users:
        try:
            uid = int(_row(row, "id"))
            stub = env.ATTENDANCE_ALARMS.getByName(str(uid))
            await stub.fetch(f"https://attendance-alarm/sync?user_id={uid}")
        except Exception as exc:
            print(
                f"[attendance-alarm-sync] user_id={_row(row,'id')} "
                f"type={type(exc).__name__} message={str(exc)[:300]}"
            )
