from context_router import classify
from core_fast_path import is_core_candidate
from intent_parser import parse


REAL_OPERATIONAL_CASES = [
    (
        "cria um lembrete hoje 9h de encontrar um lugar para armazenar jogos e emuladores",
        "tasks",
        "task_reminder",
    ),
    ("Butler, cria um lembrete amanhã 18h de entregar o relatório", "tasks", "task_reminder"),
    ("amanhã tenho que entregar o relatório do estágio", "tasks", "task_create"),
    ("preciso revisar swagger hoje", "tasks", "task_create"),
    ("preciso estudar arvore avl amanhã", "tasks", "task_create"),
    ("preciso organizar o trabalho final", "tasks", "task_create"),
    ("preciso comprar café", "grocery", "grocery_add"),
    ("me lembra de comprar café amanhã", "tasks", "task_reminder"),
    ("segunda eu não vou pra sistemas digitais", "academic", "academic_absence"),
    ("hoje não vou conseguir treinar", "workout", "workout_skip"),
    ("amanhã tenho dentista às 15h", "appointments", "appointment_create"),
    ("gastei 27 reais no almoço", "finance", "finance_expense"),
]


def test_real_operational_phrases_reach_core_router():
    for text, domain, intent in REAL_OPERATIONAL_CASES:
        route = classify(text)
        parsed = parse(text)
        assert route.domain == domain, (text, route)
        assert route.tier == "core", (text, route)
        assert parsed.domain == domain, (text, parsed)
        assert parsed.intent == intent, (text, parsed)


def test_fast_path_recognizes_direct_action_families():
    examples = [
        "cria um lembrete hoje 9h de encontrar um lugar para armazenar jogos e emuladores",
        "amanhã tenho que entregar o relatório do estágio",
        "preciso revisar swagger hoje",
        "preciso comprar café",
        "me lembra de comprar café amanhã",
        "hoje não vou conseguir treinar",
        "amanhã tenho dentista às 15h",
    ]
    for text in examples:
        assert is_core_candidate(text), text


def test_explicit_reminder_wins_over_words_from_other_domains():
    examples = [
        "me lembra de comprar café amanhã",
        "cria um lembrete de procurar jogos e emuladores hoje 9h",
        "me lembra de estudar física amanhã",
        "me lembra de ir treinar amanhã 18h",
    ]
    for text in examples:
        route = classify(text)
        assert route.domain == "tasks", (text, route)
        assert route.intent == "task_reminder", (text, route)


def test_context_switches_are_explicit_and_core_wins():
    sequences = [
        ("receita de carbonara", "queria faltar essa aula de Sistemas Digitais I", "academic"),
        ("pokemon fire red", "me lembra de entregar o relatório amanhã", "tasks"),
        ("me indica um livro brasileiro", "hoje não vou conseguir treinar", "workout"),
        ("me recomenda uma série curta", "preciso comprar arroz", "grocery"),
        ("quem foi Spinoza?", "amanhã tenho dentista às 15h", "appointments"),
    ]
    for previous, current, expected_domain in sequences:
        assert classify(previous).tier in {"library", "conversation"}
        route = classify(current)
        assert route.domain == expected_domain, (previous, current, route)
        assert route.tier == "core", (previous, current, route)


def test_casual_and_library_messages_do_not_enter_core_fast_path():
    examples = [
        "oi butler",
        "to cansado hoje",
        "kkkk",
        "quem foi Spinoza?",
        "me recomenda um filme",
        "receita de strogonoff",
        "pokemon fire red",
    ]
    for text in examples:
        assert not is_core_candidate(text), text


def test_reminder_keeps_day_hint_even_with_hour_and_cultural_words():
    parsed = parse("cria um lembrete hoje 9h de encontrar um lugar para armazenar jogos e emuladores")
    assert parsed.time_hint == "hoje"
    assert parsed.domain == "tasks"
