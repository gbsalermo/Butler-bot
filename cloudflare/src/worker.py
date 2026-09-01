"""Entrypoint de produção com alarms persistentes e diagnóstico de falhas.

O Cron Trigger continua sincronizando os alarms. Após um webhook, a reconciliação
persistente também é disparada, mas fora do caminho crítico da resposta HTTP via
``ctx.waitUntil``. Assim mantemos a redundância sem fazer o Telegram esperar uma
varredura de todos os usuários e Durable Objects antes do 200 OK.

Erros não tratados no caminho principal são persistidos em ``runtime_errors``
quando D1 estiver disponível. Isso não substitui logs Cloudflare, mas evita falha
completamente invisível ao proprietário.
"""
from urllib.parse import urlparse

from workers import Response

from entry import Default as CoreDefault
from attendance_alarm import AttendanceAlarm, sync_attendance_alarms
from personal_alarm import PersonalAlarm, sync_personal_alarms
from runtime_diagnostics import record_error


class Default(CoreDefault):
    async def _sync_persistent_alarms(self):
        try:
            await sync_attendance_alarms(self.env)
        except Exception as exc:
            print(
                f"[attendance-alarm-sync] global-error type={type(exc).__name__} "
                f"message={str(exc)[:500]}"
            )
            await record_error(self.env.DB, "attendance_alarm_sync", exc)
        try:
            await sync_personal_alarms(self.env)
        except Exception as exc:
            print(
                f"[personal-alarm-sync] global-error type={type(exc).__name__} "
                f"message={str(exc)[:500]}"
            )
            await record_error(self.env.DB, "personal_alarm_sync", exc)

    async def fetch(self, request):
        path = urlparse(request.url).path
        try:
            response = await super().fetch(request)
        except Exception as exc:
            print(
                f"[worker-fetch] path={path} type={type(exc).__name__} "
                f"message={str(exc)[:500]}"
            )
            await record_error(self.env.DB, f"fetch:{path}", exc)

            # Para webhook, uma exceção determinística não deve gerar uma tempestade
            # de retries do Telegram. O erro fica persistido e o proprietário pode
            # consultar `/status runtime`, que passa pelo primeiro handler.
            if request.method == "POST" and path == "/telegram/webhook":
                return Response("handler error recorded", status=200)
            return Response("internal error", status=500)

        # A reconciliação é importante, mas não faz parte da resposta ao usuário.
        # Antes ela era aguardada aqui: cada POST esperava SELECTs globais +
        # chamadas a Durable Objects de todos os usuários. WorkerEntrypoint expõe
        # ``self.ctx.waitUntil`` justamente para trabalho que pode continuar após
        # a resposta ser devolvida.
        if request.method == "POST" and path == "/telegram/webhook":
            self.ctx.waitUntil(self._sync_persistent_alarms())
        return response

    async def scheduled(self, controller, env, ctx):
        # No cron a reconciliação continua síncrona: aqui ela é parte do trabalho
        # do scheduler e não está atrasando uma resposta interativa do Telegram.
        await self._sync_persistent_alarms()
        try:
            await super().scheduled(controller, env, ctx)
        except Exception as exc:
            print(
                f"[worker-scheduled] type={type(exc).__name__} "
                f"message={str(exc)[:500]}"
            )
            await record_error(self.env.DB, "scheduled", exc)
            raise
