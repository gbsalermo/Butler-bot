import operational_menu


def test_manual_is_visible_in_more_and_day_off_remains_last():
    assert "📖 Manual" in [button for row in operational_menu.MORE_KB for button in row]
    assert "⚙️ Mais" in [button for row in operational_menu.MAIN_KB for button in row]
    assert operational_menu.MAIN_KB[-1] == ["🌙 Day-off"]
