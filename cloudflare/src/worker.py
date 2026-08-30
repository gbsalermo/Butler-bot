"""Entrypoint de produção com alarms persistentes para eventos pontuais.

O Cron Trigger continua sincronizando os alarms, mas um webhook também rearma os
Durable Objects depois de processar a mensagem. Assim, criar/editar um evento não
depende de o próximo tick do cron acontecer para ganhar proteção persistente.
"""
from entry import Default as CoreDefault
from attendance_alarm import AttendanceAlarm, sync_attendance_alarms
from personal_alarm import PersonalAlarm, sync_personal_alarms


class Default(CoreDefault):
    async def _sync_persistent_alarms(self):
        try:
            await sync_attendance_alarms(self.env)
        except Exception as exc:
            print(
                f"[attendance-alarm-sync] global-error type={type(exc).__name__} "
                f"message={str(exc)[:500]}"
            )
        try:
            await sync_personal_alarms(self.env)
        except Exception as exc:
            print(
                f"[personal-alarm-sync] global-error type={type(exc).__name__} "
                f"message={str(exc)[:500]}"
            )

    async def fetch(self, request):
        response = await super().fetch(request)
        # O webhook é o ponto em que tarefas, compromissos, rotinas, matérias e
        # lembretes podem ter mudado. Rearmar DEPOIS do processamento garante que
        # o novo estado já esteja no D1. GET /health não faz esse trabalho.
        if request.method == "POST":
            await self._sync_persistent_alarms()
        return response

    async def scheduled(self, controller, env, ctx):
        # Cron segue como relógio primário e também faz reconciliação dos alarms.
        await self._sync_persistent_alarms()
        await super().scheduled(controller, env, ctx)
