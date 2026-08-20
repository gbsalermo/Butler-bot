"""Entrypoint de produção com alarms persistentes para eventos pontuais."""
from entry import Default as CoreDefault
from attendance_alarm import AttendanceAlarm, sync_attendance_alarms
from personal_alarm import PersonalAlarm, sync_personal_alarms

class Default(CoreDefault):
    async def scheduled(self, controller, env, ctx):
        try:
            await sync_attendance_alarms(self.env)
        except Exception as exc:
            print(f"[attendance-alarm-sync] global-error type={type(exc).__name__} message={str(exc)[:500]}")
        try:
            await sync_personal_alarms(self.env)
        except Exception as exc:
            print(f"[personal-alarm-sync] global-error type={type(exc).__name__} message={str(exc)[:500]}")
        await super().scheduled(controller, env, ctx)
