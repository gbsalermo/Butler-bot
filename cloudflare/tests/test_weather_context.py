from weather_context import _norm
from weather_service import format_forecast


def test_weather_phrase_normalization():
    assert _norm("Previsão do tempo amanhã") == "previsao do tempo amanha"
    assert _norm("Clima em Cruz das Almas, BA") == "clima em cruz das almas ba"


def test_format_forecast_does_not_turn_peak_hour_into_whole_day_rain():
    location = {"city": "Cruz das Almas - Bahia"}
    forecast = {
        "weather_code": 51,
        "temperature_min": 20.1,
        "temperature_max": 28.4,
        "rain_probability_max": 79,
        "rain_probability_mean": 18,
        "rain_sum": 0.0,
        "rain_hours": 0,
        "cloud_cover_mean": 48,
        "wind_max": 18.6,
    }

    text = format_forecast(location, forecast, heading="Tempo hoje")

    assert "Tempo hoje — Cruz das Almas - Bahia" in text
    assert "sol entre nuvens; 20–28 °C" in text
    assert "Chuva prevista: 0.0 mm" in text
    assert "79%" not in text
    assert "Vento: até 19 km/h" in text
    assert "Fonte: Open-Meteo" in text


def test_format_forecast_with_weak_rain_uses_low_possibility_and_range():
    location = {"city": "Cruz das Almas - Bahia"}
    forecast = {
        "weather_code": 51,
        "temperature_min": 20.0,
        "temperature_max": 29.0,
        "rain_probability_max": 25,
        "rain_probability_mean": 6,
        "rain_sum": 0.4,
        "rain_hours": 4,
        "cloud_cover_mean": 52,
        "wind_max": 20.0,
    }

    text = format_forecast(location, forecast, heading="Tempo amanhã")

    assert "baixa possibilidade de chuva passageira; 20–29 °C" in text
    assert "Chuva prevista: 0.4 mm em ~4 h" in text
    assert "Chance de chuva: de 6% até 25%" in text
    assert "pico horário" not in text


def test_format_forecast_with_relevant_rain_uses_probability_range():
    location = {"city": "Cruz das Almas - Bahia"}
    forecast = {
        "weather_code": 63,
        "temperature_min": 21.4,
        "temperature_max": 28.2,
        "rain_probability_max": 80,
        "rain_probability_mean": 42,
        "rain_sum": 7.3,
        "rain_hours": 4,
        "cloud_cover_mean": 78,
        "wind_max": 19.6,
    }

    text = format_forecast(location, forecast, heading="Tempo amanhã")

    assert "Tempo amanhã — Cruz das Almas - Bahia" in text
    assert "21–28 °C" in text
    assert "Chuva prevista: 7.3 mm em ~4 h" in text
    assert "Chance de chuva: de 42% até 80%" in text
    assert "pico horário" not in text
    assert "Vento: até 20 km/h" in text
