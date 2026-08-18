"""Entrypoint de produção.

Mantém o dispatcher principal em entry.py e acrescenta a camada persistente de
alarms acadêmicos. O Cron sincroniza a agenda; os Durable Object Alarms ficam
responsáveis por acordar o Worker nos horários T-10/T0 mesmo se um tick do Cron
for perdido.
"""
from entry import Default as CoreDefault
from attendance_alarm import AttendanceAlarm, sync_attendance_alarms


class Default(CoreDefault):
    async def scheduled(self, controller, env, ctx):
        # Sincroniza primeiro para manter o próximo evento acadêmico persistido.
        try:
            await sync_attendance_alarms(self.env)
        except Exception as exc:
            print(
                f"[attendance-alarm-sync] global-error "
                f"type={type(exc).__name__} message={str(exc)[:500]}"
            )
        # Cron legado continua como redundância e cuida dos demais subsistemas.
        await super().scheduled(controller, env, ctx)
