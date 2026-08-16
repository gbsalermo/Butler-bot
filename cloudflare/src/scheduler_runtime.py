"""Execução isolada dos subsistemas agendados do Butler.

Um erro em tarefa, rotina, aula ou scheduler legado nunca deve impedir os demais.
Cloudflare captura stdout/stderr nos logs do Worker, então cada falha fica visível.
"""
from datetime import datetime, timezone


async def run_isolated(name, callback, *args):
    started=datetime.now(timezone.utc).isoformat()
    try:
        await callback(*args)
        print(f"[scheduler] ok subsystem={name} started_at={started}")
        return True
    except Exception as exc:
        print(
            f"[scheduler] error subsystem={name} started_at={started} "
            f"type={type(exc).__name__} message={str(exc)[:500]}"
        )
        return False
