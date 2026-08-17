from operational_informal_fastpath import classify
from colloquial_reminder_fastpath import _looks_like_request
from core_fast_path import is_core_candidate


def test_informal_tasks():
    assert classify("tenho que limpar a casa amanhã") == "tarefa"
    assert classify("preciso pagar a conta dia 20") == "tarefa"
    assert classify("bota como tarefa comprar ração") == "tarefa"
    assert classify("cria uma tarefa assistir entergalatic") == "tarefa"
    assert classify("crie uma tarefa revisar álgebra amanhã") == "tarefa"


def test_buttons_never_become_titles():
    assert classify("✅ Tarefa") is None
    assert classify("📅 Compromisso") is None
    assert classify("Tarefa") is None
    assert classify("Compromisso") is None


def test_informal_appointments():
    assert classify("tenho dentista amanhã 14h") == "compromisso"
    assert classify("reunião terça 10h") == "compromisso"
    assert classify("marca um compromisso com João sexta") == "compromisso"
    assert classify("cria um compromisso reunião amanhã") == "compromisso"


def test_reminder_language_is_recognized_even_without_time():
    assert _looks_like_request("me lembra de assistir entergalatic amanhã")
    assert _looks_like_request("me avisa de pagar a conta")
    assert _looks_like_request("cria um lembrete de ligar pra vó")
    assert _looks_like_request("não deixa eu esquecer de comprar ração")


def test_fast_path_candidates():
    examples = [
        "me lembra amanhã às 10h de pagar a conta",
        "me lembra de assistir entergalatic amanhã",
        "não deixa eu esquecer amanhã 9h de ligar pra vó",
        "cria uma tarefa assistir entergalatic",
        "tenho que limpar a casa amanhã",
        "dentista amanhã 14h",
        "prova de álgebra dia 24/09",
        "marca a prova de física próxima terça",
        "ovo acabou",
        "comprar milho de pipoca",
        "treino de hoje",
    ]
    for text in examples:
        assert is_core_candidate(text), text


def test_unrelated_text_does_not_enter_fast_path():
    assert not is_core_candidate("quem foi Spinoza?")
    assert not is_core_candidate("me recomenda um filme")
    assert not is_core_candidate("qual a receita de strogonoff?")
