from pathlib import Path

import app
import conversation_layer
import operational_menu
import production_usability_patch
import quality_patch


def test_final_install_keeps_operational_menu_as_source_of_truth():
    """O último patch instalado não pode recriar um menu divergente."""
    operational_menu.install()
    production_usability_patch.install()

    assert app.MAIN_KB == operational_menu.MAIN_KB
    assert app.COTIDIANO_KB == operational_menu.COTIDIANO_KB


def test_conversation_layer_does_not_define_competing_main_menu():
    """Contexto pode renderizar o menu, mas não possuir outra fonte principal."""
    assert not hasattr(conversation_layer, "MAIN_KB")


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


def test_legacy_item_reminder_layers_do_not_return():
    """`reliable_reminders` é a autoridade temporal; não recriar schedulers paralelos."""
    assert not hasattr(conversation_layer, "_pre_send_item_reminders")
    assert not hasattr(quality_patch, "_item_reminders_10_5")
    assert not Path("src/reminder_policy.py").exists()
