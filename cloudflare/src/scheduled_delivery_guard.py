"""Protege alertas agendados contra falso positivo de entrega no Telegram."""

import attendance_production_fix
import quality_patch
import reliable_reminders
import routine_integration
from telegram_api import delivery_error, delivery_ok, send_message as telegram_send_message


async def _checked_send(token, chat_id, text, reply_markup=None, parse_mode=None):
    result = await telegram_send_message(
        token,
        chat_id,
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    if not delivery_ok(result):
        error = delivery_error(result)
        print(f"[telegram-delivery] failed chat_id={chat_id} error={error}")
        raise RuntimeError(f"Telegram não confirmou entrega: {error}")
    return result


class _QualityProxy:
    """Proxy usado apenas por reliable_reminders.

    Evita trocar quality_patch.send_message globalmente e afetar respostas normais
    do webhook; somente o dispatcher agendado recebe envio confirmado.
    """
    def __getattr__(self, name):
        if name == "send_message":
            return _checked_send
        return getattr(quality_patch, name)


def install():
    # Rotinas: o log de notificação só será escrito se o send retornar sucesso.
    routine_integration.send_message = _checked_send

    # Aulas: mesma garantia antes de gravar attendance:* no notification_log.
    attendance_production_fix.send_message = _checked_send

    # Tarefas/compromissos/lembretes: proxy local, sem alterar quality_patch global.
    reliable_reminders.quality_patch = _QualityProxy()
