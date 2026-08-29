import admin_diagnostics


def test_user_status_command_aliases():
    assert admin_diagnostics._is_user_status_command("/status usuarios")
    assert admin_diagnostics._is_user_status_command("/status_usuarios")
    assert admin_diagnostics._is_user_status_command("Status de usuários")
    assert admin_diagnostics._is_user_status_command("quantos ids")


def test_user_status_rejects_unrelated_text():
    assert not admin_diagnostics._is_user_status_command("status alertas")
    assert not admin_diagnostics._is_user_status_command("minhas tarefas")


def test_user_display_helpers():
    row = {
        "preferred_name": "Chefe",
        "first_name": "Gabriel",
        "username": "gabriel",
        "created_at": "2026-08-28 14:30:00",
    }
    assert admin_diagnostics._display_name(row) == "Chefe"
    assert admin_diagnostics._created_date(row["created_at"]) == "28/08/2026"
