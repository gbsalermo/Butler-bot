import academic_polish
import app


def test_sigaa_parser_preserves_code_and_expands_multiple_weekdays():
    parsed = app.parse_schedule_text("Sistemas Digitais I 35M45 PAV II sala 05")

    assert len(parsed) == 2
    assert {item["weekday"] for item in parsed} == {"terça-feira", "quinta-feira"}
    assert all(item["name"] == "Sistemas Digitais I" for item in parsed)
    assert all(item["code"] == "35M45" for item in parsed)
    assert all(item["start"] == "10:00" for item in parsed)
    assert all(item["end"] == "12:00" for item in parsed)
    assert all(item["location"] == "PAV II sala 05" for item in parsed)


def test_sigaa_parser_handles_morning_afternoon_and_night_blocks():
    text = "\n".join(
        [
            "Cálculo I 2M23 Sala 01",
            "Física II 4T12 PAV I",
            "Programação 6N34 Lab 02",
        ]
    )
    parsed = app.parse_schedule_text(text)

    assert parsed == [
        {
            "name": "Cálculo I",
            "weekday": "segunda-feira",
            "start": "08:00",
            "end": "10:00",
            "location": "Sala 01",
            "code": "2M23",
        },
        {
            "name": "Física II",
            "weekday": "quarta-feira",
            "start": "13:00",
            "end": "15:00",
            "location": "PAV I",
            "code": "4T12",
        },
        {
            "name": "Programação",
            "weekday": "sexta-feira",
            "start": "20:00",
            "end": "22:00",
            "location": "Lab 02",
            "code": "6N34",
        },
    ]


def test_sigaa_parser_does_not_invent_schedule_from_free_text():
    assert app.parse_schedule_text("Cálculo I terça 10h sala 05") == []
    assert app.parse_schedule_text("Tenho aula amanhã de manhã") == []
    assert app.parse_schedule_text("") == []


def test_sigaa_parser_keeps_location_optional():
    parsed = app.parse_schedule_text("Álgebra Linear 2T23")
    assert len(parsed) == 1
    assert parsed[0]["location"] is None
    assert parsed[0]["code"] == "2T23"


def test_subject_edit_time_range_validation_is_strict():
    assert academic_polish._parse_time_range("08:00-09:40") == ("08:00", "09:40")
    assert academic_polish._parse_time_range("8:00 – 10:00") == ("08:00", "10:00")
    assert academic_polish._parse_time_range("10:00-09:00") is None
    assert academic_polish._parse_time_range("24:00-25:00") is None
    assert academic_polish._parse_time_range("08:70-09:00") is None


def test_subject_edit_weekday_normalization_keeps_runtime_contract():
    assert academic_polish._normalize_weekday("ter") == "terça-feira"
    assert academic_polish._normalize_weekday("terça") == "terça-feira"
    assert academic_polish._normalize_weekday("quinta feira") == "quinta-feira"
    assert academic_polish._normalize_weekday("domingo") is None


def test_onboarding_documents_recommended_sigaa_source_and_no_ocr():
    guide = academic_polish.SIGAA_SCHEDULE_GUIDE
    prompt = academic_polish.IMPORT_SCHEDULE_PROMPT

    assert "Componente Curricular" in guide
    assert "Local" in guide
    assert "Horário" in guide
    assert "PDF" in guide and ".txt" in guide
    assert "OCR" in guide

    assert "Componente Curricular" in prompt
    assert "PDF" in prompt and ".txt" in prompt
    assert "Imagem" in prompt or "imagem" in prompt
