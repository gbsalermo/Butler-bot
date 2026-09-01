import goal_operational


def test_filtered_goal_position_uses_candidates_from_shown_list():
    # A lista exibida continha somente metas de hábito: 20 era a posição 1.
    # Mesmo que a consulta atual venha em outra ordem, "1" continua sendo 20.
    current_habits = [
        {"id": 30, "name": "Beber água", "goal_type": "habit"},
        {"id": 20, "name": "Estudar inglês", "goal_type": "habit"},
    ]

    selected = goal_operational._pick_visible(
        current_habits,
        "1",
        candidate_ids=[20, 30],
    )

    assert selected["id"] == 20


def test_routine_position_uses_candidates_from_shown_list():
    current_routines = [
        {"id": 9, "name": "Academia"},
        {"id": 4, "name": "Inglês"},
    ]

    selected = goal_operational._pick_visible(
        current_routines,
        "2",
        candidate_ids=[9, 4],
    )

    assert selected["id"] == 4


def test_visible_picker_still_accepts_unique_name():
    items = [
        {"id": 4, "name": "Estudar inglês"},
        {"id": 9, "name": "Academia"},
    ]

    selected = goal_operational._pick_visible(items, "academia")

    assert selected["id"] == 9
