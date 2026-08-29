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


def test_announcement_preview_for_everyone():
    request = admin_diagnostics._parse_announcement(
        "/aviso Agora o Butler mostra a previsão do tempo junto da agenda."
    )
    assert request == {
        "confirmed": False,
        "target_user_id": None,
        "message": "Agora o Butler mostra a previsão do tempo junto da agenda.",
    }


def test_announcement_confirmation_for_everyone():
    request = admin_diagnostics._parse_announcement(
        "/aviso confirmar Nova versão disponível!"
    )
    assert request["confirmed"] is True
    assert request["target_user_id"] is None
    assert request["message"] == "Nova versão disponível!"


def test_announcement_targeted_by_internal_id():
    request = admin_diagnostics._parse_announcement(
        "/aviso confirmar id 2 Teste individual"
    )
    assert request == {
        "confirmed": True,
        "target_user_id": 2,
        "message": "Teste individual",
    }


def test_announcement_rejects_normal_conversation():
    assert admin_diagnostics._parse_announcement("avisa João sobre a novidade") is None
    assert admin_diagnostics._parse_announcement("minha agenda amanhã") is None


def test_announcement_text_has_standard_header():
    assert admin_diagnostics._announcement_text("Clima novo") == "📣 Novidades do Butler\n\nClima novo"
