from core_fast_path import is_core_candidate
from routine_natural_fastpath import (
    _completion_target,
    _looks_like_completion,
    _match_routine,
)


def _rows():
    return [
        {"id": 1, "name": "Estudar inglês", "category": "Estudos"},
        {"id": 2, "name": "Curso DIO", "category": "Programação"},
        {"id": 3, "name": "Beber água", "category": "Água"},
    ]


def test_estudei_ingles_resolve_rotina_pelo_nome_sem_abrir_menu():
    text = "estudei inglês"
    assert _looks_like_completion(text)
    assert _completion_target(text) == "ingles"
    routine, matches = _match_routine(_rows(), _completion_target(text))
    assert routine["id"] == 1
    assert [row["id"] for row in matches] == [1]
    assert is_core_candidate(text)


def test_fiz_curso_dio_resolve_rotina_com_nome_composto():
    text = "fiz o curso dio"
    assert _looks_like_completion(text)
    routine, _ = _match_routine(_rows(), _completion_target(text))
    assert routine["id"] == 2
    assert is_core_candidate(text)


def test_variantes_de_conclusao_sao_aceitas_quando_ha_alvo():
    for text in (
        "já estudei inglês",
        "cumpri curso dio",
        "completei o curso dio",
        "terminei meu curso dio",
        "pratiquei inglês",
    ):
        assert _looks_like_completion(text)
        assert is_core_candidate(text)


def test_bebi_agua_nao_encerra_rotina_inteira():
    assert not _looks_like_completion("bebi água")
    assert _completion_target("bebi água") is None


def test_match_ambiguo_nao_escolhe_no_chute():
    rows = [
        {"id": 1, "name": "Estudar inglês", "category": "Inglês"},
        {"id": 2, "name": "Curso de inglês", "category": "Inglês"},
    ]
    routine, matches = _match_routine(rows, "ingles")
    assert routine is None
    assert len(matches) == 2
