import conversation_layer


async def _noop_item_reminders(db, token):
    # A politica de lembretes agora vive exclusivamente em reliable_reminders.py.
    # Evita duplicidade e regras antigas de aviso antecipado para tarefas.
    return None


def install():
    conversation_layer._pre_send_item_reminders = _noop_item_reminders
