import asyncio

import entry


def _handler(name, calls, result=False):
    async def fake(_db, _token, _payload):
        calls.append(name)
        return result

    return fake


def test_admin_announcement_preview_wins_before_admin_diagnostics(monkeypatch):
    calls = []
    monkeypatch.setattr(entry, "handle_start_reset", _handler("start", calls, False))
    monkeypatch.setattr(
        entry,
        "handle_admin_announcement_preview",
        _handler("announcement", calls, True),
    )

    async def must_not_run(*_args, **_kwargs):
        raise AssertionError("diagnóstico não pode executar após o aviso consumir a mensagem")

    monkeypatch.setattr(entry, "handle_admin_diagnostics", must_not_run)

    handled = asyncio.run(
        entry.dispatch_message(
            object(),
            "token",
            {"text": "/aviso novidade", "chat": {"id": 10}},
        )
    )

    assert handled is True
    assert calls == ["start", "announcement"]


def test_admin_callback_has_priority_over_other_callbacks(monkeypatch):
    calls = []
    monkeypatch.setattr(
        entry,
        "handle_admin_announcement_callback",
        _handler("admin", calls, True),
    )

    async def must_not_run(*_args, **_kwargs):
        raise AssertionError("callback posterior não pode executar após consumo")

    monkeypatch.setattr(entry, "handle_attendance_callback", must_not_run)
    monkeypatch.setattr(entry, "handle_context_callback", must_not_run)

    handled = asyncio.run(
        entry.dispatch_callback(
            object(),
            "token",
            {"data": "admin_notice:send:abcdef123456", "id": "cb1"},
        )
    )

    assert handled is True
    assert calls == ["admin"]


def test_callback_falls_through_in_declared_order(monkeypatch):
    calls = []
    monkeypatch.setattr(
        entry,
        "handle_admin_announcement_callback",
        _handler("admin", calls, False),
    )
    monkeypatch.setattr(
        entry,
        "handle_attendance_callback",
        _handler("attendance", calls, False),
    )
    monkeypatch.setattr(
        entry,
        "handle_context_callback",
        _handler("context", calls, True),
    )

    handled = asyncio.run(entry.dispatch_callback(object(), "token", {"data": "item:done:1"}))

    assert handled is True
    assert calls == ["admin", "attendance", "context"]


def test_cron_subsystems_keep_authoritative_order(monkeypatch):
    calls = []

    async def fake_run_isolated(label, _fn, *_args):
        calls.append(label)

    monkeypatch.setattr(entry, "run_isolated", fake_run_isolated)

    asyncio.run(entry.dispatch_scheduled(object(), "token"))

    assert calls == [
        "day_off",
        "attendance",
        "daily_items",
        "routines",
        "summaries",
        "legacy",
    ]


def test_general_dispatch_does_not_run_attendance_ddl_before_handlers(monkeypatch):
    """Migration 0003 é a fonte do schema; conversa comum não pode pagar DDL."""
    calls = []

    early_false = (
        "handle_start_reset",
        "handle_admin_announcement_preview",
        "handle_admin_diagnostics",
        "handle_alert_diagnostics",
        "handle_production_usability",
        "handle_operational_menu",
        "handle_routine_ui",
        "handle_routine_editing",
        "handle_attendance_production_ui",
        "handle_global_navigation",
        "handle_core_fast_path",
    )
    for name in early_false:
        monkeypatch.setattr(entry, name, _handler(name, calls, False))

    monkeypatch.setattr(entry, "is_priority_farewell", lambda _text: False)
    monkeypatch.setattr(
        entry,
        "handle_attendance_management",
        _handler("attendance_management", calls, True),
    )

    class _NoDB:
        def prepare(self, sql):
            raise AssertionError(f"dispatcher geral não deveria executar SQL antes do handler: {sql}")

    handled = asyncio.run(
        entry.dispatch_message(
            _NoDB(),
            "token",
            {"text": "faltas", "chat": {"id": 10}},
        )
    )

    assert handled is True
    assert calls[-1] == "attendance_management"
