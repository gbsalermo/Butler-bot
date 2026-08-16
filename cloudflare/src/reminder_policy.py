import conversation_layer
from attendance_manual import install as install_attendance_manual
from exam_reminder_guard import install as install_exam_reminder_guard


async def _noop_item_reminders(db, token):
    # A politica de lembretes agora vive exclusivamente em reliable_reminders.py.
    # Evita duplicidade e regras antigas de aviso antecipado para tarefas.
    return None


def install():
    conversation_layer._pre_send_item_reminders = _noop_item_reminders
    install_attendance_manual()
    install_exam_reminder_guard()
