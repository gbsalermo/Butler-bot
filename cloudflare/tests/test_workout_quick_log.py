from workout_quick_log import parse_quick_series


def test_registro_rapido_aceita_mensagem_autossuficiente():
    assert parse_quick_series("Supino reto | 40 kg | 10 reps") == (
        "Supino reto", "40 kg", "10 reps"
    )


def test_registro_rapido_aceita_progressao_em_mensagens_separadas():
    messages=[
        "Supino reto | 40 kg | 12 reps",
        "Supino reto | 45 kg | 10 reps",
        "Supino reto | 50 kg | 8 reps",
    ]
    parsed=[parse_quick_series(text) for text in messages]
    assert [item[1] for item in parsed] == ["40 kg","45 kg","50 kg"]


def test_registro_rapido_nao_intercepta_conversa_comum():
    assert parse_quick_series("hoje vou treinar peito") is None
    assert parse_quick_series("Supino | pesado | dez") is None
