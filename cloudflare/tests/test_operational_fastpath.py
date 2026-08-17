from operational_informal_fastpath import classify
from core_fast_path import is_core_candidate


def test_informal_tasks():
    assert classify("tenho que limpar a casa amanhã") == "tarefa"
    assert classify("preciso pagar a conta dia 20") == "tarefa"
    assert classify("bota como tarefa comprar ração") == "tarefa"


def test_informal_appointments():
    assert classify("tenho dentista amanhã 14h") == "compromisso"
    assert classify("reunião terça 10h") == "compromisso"
    assert classify("marca um compromisso com João sexta") == "compromisso"


def test_fast_path_candidates():
    examples = [
        "me lembra amanhã às 10h de pagar a conta",
        "não deixa eu esquecer amanhã 9h de ligar pra vó",
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
