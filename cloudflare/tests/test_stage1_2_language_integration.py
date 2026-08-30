import language_primitives as lp
from colloquial_reminder_fastpath import _looks_like_request
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
    ]
    for text in cases:
        assert "reminder" in lp.detect_action_families(text)
        assert _looks_like_request(text)


def test_task_and_appointment_classifier_aligns_with_common_families():
    task_cases = [
        "tenho que limpar a casa amanhã",
        "cria uma tarefa revisar álgebra",
    ]
    appointment_cases = [
        "tenho dentista amanhã 14h",
        "cria um compromisso reunião amanhã",
    ]
    for text in task_cases:
        assert "create_task" in lp.detect_action_families(text)
        assert classify(text) == "tarefa"
    for text in appointment_cases:
        assert "create_appointment" in lp.detect_action_families(text)
        assert classify(text) == "compromisso"


def test_negated_reminder_action_is_not_executed_as_positive_request():
    text = "não me lembra de estudar hoje"
    assert "reminder" in lp.detect_action_families(text)
    assert lp.negation_scope(text) == "action"
    assert not _looks_like_request(text)


def test_negated_target_remains_a_valid_reminder_request():
    text = "me lembra de não estudar hoje"
    assert "reminder" in lp.detect_action_families(text)
    assert lp.negation_scope(text) == "target"
    assert _looks_like_request(text)
