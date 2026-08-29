import asyncio
from datetime import datetime
from pathlib import Path

from day_off_policy import LOCAL_TZ, expire_stale_day_offs, is_day_off_active


def local_dt(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=LOCAL_TZ)


def test_day_off_is_valid_only_on_activation_local_date_even_across_utc_midnight():
    # Sábado 22/08 às 23:30 na Bahia vira domingo 23/08 02:30 em UTC/D1.
    activated_at_utc = "2026-08-23 02:30:00"

    assert is_day_off_active(1, activated_at_utc, now=local_dt(2026, 8, 22, 23, 45))
    assert not is_day_off_active(1, activated_at_utc, now=local_dt(2026, 8, 23, 0, 1))


def test_weekend_is_not_day_off_by_itself():
    saturday = local_dt(2026, 8, 22, 12)
    sunday = local_dt(2026, 8, 23, 12)

    assert not is_day_off_active(0, "2026-08-22 15:00:00", now=saturday)
    assert not is_day_off_active(0, "2026-08-23 15:00:00", now=sunday)


def test_legacy_or_invalid_timestamp_cannot_silence_butler_forever():
    assert not is_day_off_active(1, None, now=local_dt(2026, 8, 23))
    assert not is_day_off_active(1, "timestamp-invalido", now=local_dt(2026, 8, 23))


class _Result:
    def __init__(self, rows):
        self.results = rows


class _Statement:
    def __init__(self, db, sql):
        self.db = db
        self.sql = sql
        self.params = ()

    def bind(self, *params):
        self.params = params
        return self

    async def all(self):
        return _Result([dict(row) for row in self.db.rows if row["day_off"] == 1])

    async def run(self):
        if self.sql.startswith("UPDATE assistant_state SET day_off=0"):
            uid = int(self.params[0])
            for row in self.db.rows:
                if row["user_id"] == uid and row["day_off"] == 1:
                    row["day_off"] = 0
        return None


class _DB:
    def __init__(self, rows):
        self.rows = rows

    def prepare(self, sql):
        return _Statement(self, sql)


def test_expire_stale_day_offs_clears_previous_day_and_keeps_today():
    db = _DB(
        [
            {"user_id": 1, "day_off": 1, "updated_at": "2026-08-22 15:00:00"},
            {"user_id": 2, "day_off": 1, "updated_at": "2026-08-23 15:00:00"},
            {"user_id": 3, "day_off": 0, "updated_at": "2026-08-22 15:00:00"},
        ]
    )

    expired = asyncio.run(
        expire_stale_day_offs(db, now=local_dt(2026, 8, 23, 13))
    )

    assert expired == 1
    assert db.rows[0]["day_off"] == 0
    assert db.rows[1]["day_off"] == 1
    assert db.rows[2]["day_off"] == 0


def test_entry_expires_day_off_before_dispatch_and_cron_starts_with_day_off():
    """Protege a política, não a implementação antiga de handlers inline."""
    source = Path("src/entry.py").read_text(encoding="utf-8")

    webhook_expire = source.index("await expire_stale_day_offs(self.env.DB)")
    webhook_dispatch = source.index("await dispatch_message(self.env.DB, token, message)")
    assert webhook_expire < webhook_dispatch

    cron_expire = source.index('await run_isolated("day_off", expire_stale_day_offs, db)')
    cron_attendance = source.index('await run_isolated("attendance", _attendance_tick, db, token)')
    assert cron_expire < cron_attendance
    assert '"weekend_is_not_automatic_day_off": True' in source
