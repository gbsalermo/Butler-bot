"""Alarms persistentes para lembretes pessoais e checkpoints de rotina.
Cron sincroniza; Durable Object acorda o Butler no horário marcado.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from workers import DurableObject, Response
from settings import UTC_OFFSET_HOURS
from reliable_reminders import dispatch_due_reminders
from routine_integration import _routine_reminders, _applies, _times

LOCAL_TZ=timezone(timedelta(hours=UTC_OFFSET_HOURS))

def _row(row,key,default=None):
    try:return getattr(row,key)
    except Exception:
        try:return row[key]
        except Exception:return default
async def _rows(stmt):
    r=await stmt.all(); d=getattr(r,"results",None)
    if d is None:return []
    try:return list(d)
    except Exception:return d.to_py() if hasattr(d,"to_py") else []

async def _next_event(db,uid,now=None):
    now=now or datetime.now(timezone.utc).astimezone(LOCAL_TZ); candidates=[]; today=now.date()
    items=await _rows(db.prepare("SELECT id,due_date,due_time,details,status FROM daily_items WHERE user_id=? AND status='pendente' AND due_time IS NOT NULL AND due_date>=? ORDER BY due_date,due_time LIMIT 100").bind(uid,today.isoformat()))
    for item in items:
        # Apenas lembretes pessoais aqui; compromissos/tarefas continuam no dispatcher próprio.
        if (_row(item,"details") or "")!="simple_reminder":continue
        try:
            day=datetime.strptime(_row(item,"due_date"),"%Y-%m-%d").date(); h,m=map(int,_row(item,"due_time").split(":")); when=datetime.combine(day,datetime.min.time()).replace(hour=h,minute=m,tzinfo=LOCAL_TZ)
        except Exception:continue
        key=f"item:new:{int(_row(item,'id'))}:{day.isoformat()}:{when.strftime('%H:%M')}"
        sent=await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid,key).first()
        if not sent and when>=now-timedelta(minutes=2):candidates.append(when if when>now else now+timedelta(seconds=1))
    routines=await _rows(db.prepare("SELECT id,name,time_hhmm,weekdays FROM routines WHERE user_id=? AND active=1 AND time_hhmm IS NOT NULL").bind(uid))
    for routine in routines:
        if not _applies(_row(routine,"weekdays"),today):continue
        rid=int(_row(routine,"id"))
        for t in _times(_row(routine,"time_hhmm")):
            try:h,m=map(int,t.split(":")); when=datetime.combine(today,datetime.min.time()).replace(hour=h,minute=m,tzinfo=LOCAL_TZ)
            except Exception:continue
            key=f"routine:{rid}:{today.isoformat()}:{t}"
            sent=await db.prepare("SELECT id FROM notification_log WHERE user_id=? AND notification_key=?").bind(uid,key).first()
            if not sent and when>=now-timedelta(minutes=2):candidates.append(when if when>now else now+timedelta(seconds=1))
    return min(candidates) if candidates else None

class PersonalAlarm(DurableObject):
    def __init__(self,ctx,env):
        super().__init__(ctx,env); self.storage=ctx.storage; self.env=env
    async def fetch(self,request):
        raw=(parse_qs(urlparse(request.url).query).get("user_id") or [None])[0]
        if raw is None:return Response("missing user_id",status=400)
        try:uid=int(raw)
        except Exception:return Response("invalid user_id",status=400)
        await self.storage.put("user_id",uid); await self._schedule(uid); return Response("ok")
    async def _schedule(self,uid):
        when=await _next_event(self.env.DB,uid)
        if when is None:
            try:self.storage.deleteAlarm()
            except Exception:pass
            return
        self.storage.setAlarm(int(when.timestamp()*1000))
    async def alarm(self,alarm_info=None):
        uid=await self.storage.get("user_id")
        if uid is None:return
        # Dispatchers continuam idempotentes via notification_log e envio confirmado.
        await dispatch_due_reminders(self.env.DB,self.env.TELEGRAM_BOT_TOKEN)
        await _routine_reminders(self.env.DB,self.env.TELEGRAM_BOT_TOKEN)
        await self._schedule(int(uid))

async def sync_personal_alarms(env):
    users=await _rows(env.DB.prepare("SELECT id FROM users"))
    for row in users:
        try:
            uid=int(_row(row,"id")); stub=env.PERSONAL_ALARMS.getByName(str(uid)); await stub.fetch(f"https://personal-alarm/sync?user_id={uid}")
        except Exception as exc:print(f"[personal-alarm-sync] user_id={_row(row,'id')} type={type(exc).__name__} message={str(exc)[:300]}")
