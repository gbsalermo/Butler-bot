"""Entrypoint de produção com alarms persistentes para eventos pontuais.

O Cron Trigger continua sincronizando os alarms. Após um webhook, a reconciliação
persistente também é disparada, mas fora do caminho crítico da resposta HTTP via
``ctx.waitUntil``. Assim mantemos a redundância sem fazer o Telegram esperar uma
varredura de todos os usuários e Durable Objects antes do 200 OK.
"""
from urllib.parse import urlparse

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

        # A reconciliação é importante, mas não faz parte da resposta ao usuário.
        # Antes ela era aguardada aqui: cada POST esperava SELECTs globais +
        # chamadas a Durable Objects de todos os usuários. WorkerEntrypoint expõe
        # ``self.ctx.waitUntil`` justamente para trabalho que pode continuar após
        # a resposta ser devolvida.
        path = urlparse(request.url).path
        if request.method == "POST" and path == "/telegram/webhook":
            self.ctx.waitUntil(self._sync_persistent_alarms())
        return response

    async def scheduled(self, controller, env, ctx):
        # No cron a reconciliação continua síncrona: aqui ela é parte do trabalho
        # do scheduler e não está atrasando uma resposta interativa do Telegram.
        await self._sync_persistent_alarms()
        await super().scheduled(controller, env, ctx)
