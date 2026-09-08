from core_fast_path import is_core_candidate
from routine_natural_fastpath import _extract_name, _looks_like_create


def test_criar_outra_rotina_entra_no_fastpath():
    text = "cria outra rotina de Academia segunda, quarta e sexta às 19h"
    assert _looks_like_create(text)
    assert _extract_name(text) == "Academia"
    assert is_core_candidate(text)


def test_adicionar_mais_uma_rotina_entra_no_fastpath():
    text = "adiciona mais uma rotina Curso DIO todos os dias 20h"
    assert _looks_like_create(text)
    assert _extract_name(text) == "Curso DIO"
    assert is_core_candidate(text)


def test_sequencia_natural_de_varias_rotinas_nao_perde_o_segundo_pedido():
    requests = [
        ("cria uma rotina de Estudar inglês terça e quinta às 18h", "Estudar inglês"),
        ("cria outra rotina de Academia segunda, quarta e sexta às 19h", "Academia"),
        ("adiciona mais uma rotina Curso DIO todos os dias 20h", "Curso DIO"),
    ]

    for text, expected_name in requests:
        assert _looks_like_create(text)
        assert _extract_name(text) == expected_name
        assert is_core_candidate(text)
