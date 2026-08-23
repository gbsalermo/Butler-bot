"""Desativa a política antiga de itens da ``conversation_layer``.

A produção mantém ``app.scheduled_tick`` e partes da ``conversation_layer`` por
compatibilidade, mas tarefas/compromissos/lembretes simples passaram a ser
responsabilidade de ``reliable_reminders.py``.

Este módulo parece um NOOP, porém é funcionalmente importante: ele impede que a
política antiga seja executada em paralelo e gere avisos duplicados ou com outro
adiantamento. Sua posição em ``entry.py`` deve permanecer depois de patches que
possam reinstalar ``conversation_layer._pre_send_item_reminders``.
"""

import conversation_layer


async def _noop_item_reminders(db, token):
    """Consumidor vazio instalado no ponto onde o scheduler antigo chamaria itens."""
    return None


def install():
    """Deixa ``reliable_reminders`` como única autoridade temporal desses itens."""
    conversation_layer._pre_send_item_reminders = _noop_item_reminders
