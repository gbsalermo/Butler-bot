import operational_menu


def test_manual_is_visible_and_day_off_remains_last():
    assert ["📖 Manual"] in operational_menu.MAIN_KB
    assert operational_menu.MAIN_KB[-1] == ["🌙 Day-off"]
    assert operational_menu.MAIN_KB.index(["📖 Manual"]) < operational_menu.MAIN_KB.index(["🌙 Day-off"])
