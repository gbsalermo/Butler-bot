from reliable_summaries import _agenda_brief, _join_names


def test_join_names_reads_naturally():
    assert _join_names(["Sistemas Digitais", "Cálculo"]) == "Sistemas Digitais e Cálculo"
    assert _join_names(["A", "B", "C"]) == "A, B e C"


def test_brief_prioritizes_untimed_tasks_and_avoids_full_agenda_dump():
    classes = [
        {"name": "Sistemas Digitais", "start_time": "08:00"},
        {"name": "Cálculo", "start_time": "10:00"},
    ]
    tasks = [
        {"title": "Entregar lista", "due_time": None},
        {"title": "Enviar relatório", "due_time": "09:30"},
        {"title": "Reunião do projeto", "due_time": "11:00"},
    ]

    text = _agenda_brief(classes, tasks, [])

    assert "Sistemas Digitais e Cálculo" in text
    assert "Eu te aviso" in text
    assert "Entregar lista" in text
    assert "2 tarefas têm horário" in text
    assert "Enviar relatório" not in text
    assert "Reunião do projeto" not in text


def test_brief_is_short_when_morning_is_free():
    assert _agenda_brief([], [], []) == "A manhã está mais livre por enquanto."
