import app
import operational_menu
import production_usability_patch


def test_final_install_keeps_operational_menu_as_source_of_truth():
    """O último patch instalado não pode recriar um menu divergente."""
    operational_menu.install()
    production_usability_patch.install()

    assert app.MAIN_KB == operational_menu.MAIN_KB
    assert app.COTIDIANO_KB == operational_menu.COTIDIANO_KB


def test_finance_stays_hidden_from_primary_cotidiano_menu():
    """Contrato declarado pelo /health: Finanças não volta por navegação de fallback."""
    operational_menu.install()
    production_usability_patch.install()

    labels = [label for row in app.COTIDIANO_KB for label in row]
    assert "💰 Finanças" not in labels


def test_day_off_remains_last_main_menu_row():
    operational_menu.install()
    production_usability_patch.install()

    assert app.MAIN_KB[-1] == ["🌙 Day-off"]
