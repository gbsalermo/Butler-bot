"""Escopo diário do modo Day-off.

Day-off é uma pausa explícita do Butler apenas para o dia local em que foi
ativado. Ele nunca representa "fim de semana" e nunca deve atravessar a
meia-noite silenciosamente.

A tabela atual já possui ``day_off`` e ``updated_at``. Como ``updated_at`` é
atualizado justamente ao ativar/desativar o modo, ele funciona como carimbo de
ativação sem exigir migration adicional. O timestamp SQLite é UTC; a comparação
é feita após conversão para o offset local configurado em ``settings.py``.
"""

from datetime import datetime, timedelta, timezone

from settings import UTC_OFFSET_HOURS

LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


def _rows_from_result(result):
    data = getattr(result, "results", None)
    if data is None:
        return []
    try:
        return list(data)
    except Exception:
        return data.to_py() if hasattr(data, "to_py") else []


def _parse_updated_at(value):
    """Interpreta ``CURRENT_TIMESTAMP`` do SQLite/D1 como UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except Exception:
            try:
                dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ)


def is_day_off_active(day_off, updated_at, now=None):
    """True somente durante a mesma data local em que Day-off foi ativado."""
    try:
        enabled = bool(int(day_off or 0))
    except Exception:
        enabled = False
    if not enabled:
        return False

    activated = _parse_updated_at(updated_at)
    if activated is None:
        # Estado antigo/ambíguo não pode silenciar o Butler indefinidamente.
        return False

    local_now = now or datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=LOCAL_TZ)
    else:
        local_now = local_now.astimezone(LOCAL_TZ)
    return activated.date() == local_now.date()


async def expire_stale_day_offs(db, now=None):
    """Desativa Day-off de dias anteriores e retorna quantos foram expirados.

    É chamado antes de mensagens e antes do cron. Assim, mesmo que um ciclo do
    scheduler falhe, a próxima interação do usuário também recupera o Butler.
    """
    result = await db.prepare(
        "SELECT user_id,day_off,updated_at FROM assistant_state WHERE day_off=1"
    ).all()
    rows = _rows_from_result(result)
    expired = 0
    for row in rows:
        if is_day_off_active(_row(row, "day_off", 0), _row(row, "updated_at"), now=now):
            continue
        uid = _row(row, "user_id")
        if uid is None:
            continue
        await db.prepare(
            "UPDATE assistant_state SET day_off=0,updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND day_off=1"
        ).bind(int(uid)).run()
        expired += 1
    return expired
