"""Protege alertas agendados contra falso positivo e contra avisos obsoletos."""
import re
import academic_intelligence
import attendance_production_fix
import quality_patch
import reliable_exam_reminders
import reliable_reminders
import routine_integration
from telegram_api import delivery_error, delivery_ok, send_message as telegram_send_message

MAX_ROUTINE_DELAY_MINUTES = 2

async def _checked_send(token, chat_id, text, reply_markup=None, parse_mode=None):
    # Rotina 20:00 chegando 21:10 não é lembrete, é autópsia. Se o cron perdeu
    # a janela útil, suprimimos o envio tardio. O scheduler roda a cada minuto,
    # portanto 0-2 min cobre a resolução operacional sem aceitar atrasos absurdos.
    if (text or "").startswith("🧘 Rotina —"):
        m = re.search(r"aviso atrasou\s+(\d+)\s+min", text or "", re.I)
        if m and int(m.group(1)) > MAX_ROUTINE_DELAY_MINUTES:
            print(f"[routine-delivery] stale-suppressed chat_id={chat_id} late_minutes={m.group(1)}")
            return {"ok": True, "suppressed_stale": True}

    result = await telegram_send_message(token, chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    if not delivery_ok(result):
        error = delivery_error(result)
        print(f"[telegram-delivery] failed chat_id={chat_id} error={error}")
        raise RuntimeError(f"Telegram não confirmou entrega: {error}")
    return result

class _QualityProxy:
    def __getattr__(self, name):
        if name == "send_message": return _checked_send
        return getattr(quality_patch, name)

def install():
    routine_integration.send_message = _checked_send
    attendance_production_fix.send_message = _checked_send
    reliable_reminders.quality_patch = _QualityProxy()
    academic_intelligence.exam_reminders = reliable_exam_reminders.exam_reminders
