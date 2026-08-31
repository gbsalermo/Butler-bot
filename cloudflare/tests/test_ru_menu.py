from datetime import date

import ru_menu


SAMPLE = """
CARDAPIO RU
SEMANA: 31/08/2026 a 05/09/2026

[SEGUNDA - 31/08/2026]
CAFE
Bebida: Café preto / café com leite
Proteína: Queijo
Vegetariano: Patê de lentilha

ALMOCO
Acompanhamento 01: Feijão carioca
Proteína 01: Frango assado
Vegetariano: Moqueca de ovo

JANTAR
Sopa: Sopa de legumes
Proteína: Carne em cubos

[TERCA - 01/09/2026]
CAFE
Bebida: Suco de frutas
Proteína: Ovos mexidos

ALMOCO
Proteína 01: Lombo suíno ao molho
"""


def test_parse_ru_menu_structured_txt():
    parsed = ru_menu.parse_ru_menu_text(SAMPLE)

    assert parsed is not None
    assert parsed["week_start"] == "2026-08-31"
    assert parsed["week_end"] == "2026-09-05"
    assert [day["date"] for day in parsed["days"]] == ["2026-08-31", "2026-09-01"]

    monday = parsed["days"][0]["meals"]
    assert monday["cafe"][0] == {"label": "Bebida", "value": "Café preto / café com leite"}
    assert monday["almoco"][1]["value"] == "Frango assado"
    assert monday["jantar"][0]["value"] == "Sopa de legumes"


def test_period_line_is_not_treated_as_a_day_heading():
    parsed = ru_menu.parse_ru_menu_text(
        """SEMANA: 31/08/2026 a 05/09/2026
SEGUNDA
ALMOCO
Proteína: Frango assado
"""
    )
    assert parsed is not None
    assert parsed["days"] == [
        {
            "date": "2026-08-31",
            "meals": {"almoco": [{"label": "Proteína", "value": "Frango assado"}]},
        }
    ]


def test_ru_query_gate_accepts_expected_phrases_and_avoids_statement():
    assert ru_menu._looks_ru("qual o almoço hoje?")
    assert ru_menu._looks_ru("qual o cafe amanha")
    assert ru_menu._looks_ru("vegetariano amanhã")
    assert ru_menu._looks_ru("quais dias dessa semana tem carne?")
    assert ru_menu._looks_ru("o que vai ter no RU hoje?")
    assert not ru_menu._looks_ru("almoço com João amanhã")


def test_date_meal_and_food_resolution():
    today = date(2026, 8, 31)

    assert ru_menu._target_date("janta de quarta?", today) == date(2026, 9, 2)
    assert ru_menu._target_date("qual o cafe amanha", today) == date(2026, 9, 1)
    assert ru_menu._requested_meal("tem frango hoje no almoço?") == "almoco"
    assert ru_menu._keyword("tem frango hoje no almoço?") == "frango"
    assert ru_menu._keyword("quais dias dessa semana tem carne?") == "carne"
