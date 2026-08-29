import admin_announcement_flow
import admin_diagnostics


def test_callback_data_round_trip():
    key = "abcdef123456"
    data = admin_announcement_flow._callback_data("send", key)
    assert data == "admin_notice:send:abcdef123456"
    assert admin_announcement_flow._parse_callback(data) == {
        "action": "send",
        "pending_key": key,
    }


def test_callback_parser_rejects_unrelated_data():
    assert admin_announcement_flow._parse_callback("attendance:yes:1") is None
    assert admin_announcement_flow._parse_callback("admin_notice:send:too-short") is None


def test_confirmation_keyboard_has_send_and_cancel_buttons():
    keyboard = admin_announcement_flow._confirmation_keyboard("abcdef123456")
    buttons = keyboard["inline_keyboard"][0]
    assert buttons[0]["text"] == "✅ Confirmar envio"
    assert buttons[0]["callback_data"] == "admin_notice:send:abcdef123456"
    assert buttons[1]["text"] == "❌ Cancelar"
    assert buttons[1]["callback_data"] == "admin_notice:cancel:abcdef123456"


def test_preview_request_only_intercepts_unconfirmed_notice():
    preview = admin_diagnostics._parse_announcement("/aviso Testando novidade")
    legacy_confirm = admin_diagnostics._parse_announcement("/aviso confirmar Testando novidade")
    assert admin_announcement_flow._is_preview_request(preview)
    assert not admin_announcement_flow._is_preview_request(legacy_confirm)
