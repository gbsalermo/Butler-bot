from datetime import date, datetime

from src.natural_language import interpret, validate_future

TODAY = date(2026, 8, 14)


def expect(text, intent_name):
    result = interpret(text, TODAY)
    assert result is not None, f"Sem intenção: {text}"
    assert result.name == intent_name, f"{text!r}: esperado {intent_name}, veio {result.name} ({result.data})"
    return result


def main():
    r = expect("Butler, amanhã tenho dentista às 15h", "appointment_create")
    assert r.data["date"] == date(2026, 8, 15) and r.data["time"] == "15:00" and r.data["title"].lower() == "dentista"

    r = expect("amanhã preciso entregar o relatório às 18h", "task_create")
    assert r.data["date"] == date(2026, 8, 15) and r.data["time"] == "18:00" and "relatório" in r.data["title"].lower()

    r = expect("o que tenho daqui a 3 dias?", "agenda_query")
    assert r.data["date"] == date(2026, 8, 17)

    r = expect("falta sal, açúcar e café", "grocery_add")
    assert len(r.data["items"]) == 3

    r = expect("bota café na lista de mercado", "grocery_add")
    assert r.data["items"] == ["café"]

    expect("o que falta em casa?", "grocery_query")
    expect("comprei o café", "grocery_bought")

    r = expect("hoje não vou treinar porque estou cansado", "workout_skip")
    assert r.data["reason"].lower() == "estou cansado"

    r = expect("vou me atrasar para o dentista", "late_notice")
    assert "dentista" in (r.data["target"] or "").lower()

    r = expect("gastei 35 com lanche", "finance_add")
    assert r.data["kind"] == "saida" and r.data["amount"] == 35.0

    r = expect("recebi 540 de bolsa", "finance_add")
    assert r.data["kind"] == "entrada" and r.data["amount"] == 540.0

    ok, _ = validate_future(date(2026, 8, 13), "15:00", datetime(2026, 8, 14, 10, 0))
    assert not ok
    ok, _ = validate_future(date(2026, 8, 14), "09:00", datetime(2026, 8, 14, 10, 0))
    assert not ok
    ok, _ = validate_future(date(2026, 8, 14), "11:00", datetime(2026, 8, 14, 10, 0))
    assert ok

    print("NLU smoke OK")


if __name__ == "__main__":
    main()
