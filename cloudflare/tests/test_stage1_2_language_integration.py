import inspect

import language_primitives as lp
import natural_behavior_patch
from colloquial_reminder_fastpath import _looks_like_request
from core_fast_path import is_core_candidate
from operational_informal_fastpath import classify


def test_common_normalizer_preserves_temporal_separators_when_requested():
    assert lp.normalize_text("Butler, amanhã às 15:30!", keep_temporal=True) == "butler amanha as 15:30"


def test_reminder_fastpath_uses_common_action_family():
    cases = [
        "me lembra de estudar amanhã",
        "me lembre de pagar a conta",
        "me avisa de ligar pra vó",
        "me recorda de comprar café",
        "não deixa eu esquecer de levar o documento",
        "me dá um toque pra revisar álgebra",
        "cria um lembrete de beber água",
        "criar um lembrete de renovar o documento",
    ]
    for text in cases:
        assert "reminder" in lp.detect_action_families(text)
        assert _looks_like_request(text)
        assert is_core_candidate(text)


def test_task_and_appointment_classifier_aligns_with_common_families():
    task_cases = [
        "tenho que limpar a casa amanhã",
        "preciso pagar a conta dia 20",
        "cria uma tarefa revisar álgebra",
        "criar uma tarefa terminar o front",
    ]
    appointment_cases = [
        "tenho dentista amanhã 14h",
        "cria um compromisso reunião amanhã",
        "criar um compromisso reunião sexta",
    ]
    for text in task_cases:
        assert "create_task" in lp.detect_action_families(text)
        assert classify(text) == "tarefa"
        assert is_core_candidate(text)
    for text in appointment_cases:
        assert "create_appointment" in lp.detect_action_families(text)
        assert classify(text) == "compromisso"
        assert is_core_candidate(text)


def test_preciso_is_not_a_blanket_task_trigger_anymore():
    assert classify("preciso pagar a conta") == "tarefa"
    assert classify("preciso de ajuda com cálculo") is None
    assert not is_core_candidate("preciso de ajuda com cálculo")


def test_negated_reminder_action_is_not_executed_as_positive_request():
    text = "não me lembra de estudar hoje"
    assert "reminder" in lp.detect_action_families(text)
    assert lp.negation_scope(text) == "action"
    assert lp.action_polarity(text, "reminder") == "negative"
    assert not _looks_like_request(text)
    assert not is_core_candidate(text)


def test_negated_target_remains_a_valid_reminder_request():
    text = "me lembra de não estudar hoje"
    assert "reminder" in lp.detect_action_families(text)
    assert lp.negation_scope(text) == "target"
    assert lp.action_polarity(text, "reminder") == "positive"
    assert _looks_like_request(text)


def test_nao_deixa_eu_esquecer_is_positive_idiom():
    text = "não deixa eu esquecer de comprar café"
    assert lp.negation_scope(text) == "action"
    assert lp.action_polarity(text, "reminder") == "positive"
    assert _looks_like_request(text)


def test_natural_behavior_no_longer_persists_reminders_itself():
    source = inspect.getsource(natural_behavior_patch.handle_explicit_simple_reminder)
    assert "colloquial_reminder_fastpath" in source
    assert "INSERT INTO daily_items" not in source


def test_task_wording_never_becomes_simple_reminder():
    text = "criar uma tarefa revisar cálculo amanhã às 20h"
    assert "create_task" in lp.detect_action_families(text)
    assert "reminder" not in lp.detect_action_families(text)
    assert classify(text) == "tarefa"
