from weather_context import _norm
from weather_service import format_forecast


def test_weather_phrase_normalization():
    assert _norm("Previsão do tempo amanhã") == "previsao do tempo amanha"
    assert _norm("Clima em Cruz das Almas, BA") == "clima em cruz das almas ba"


def test_format_forecast_does_not_treat_hourly_peak_as_all_day_rain():
    location = {"city": "Cruz das Almas - BA"}
    forecast = {
        # O WMO diário pode carregar a condição mais severa do dia, mesmo com
        # volume praticamente nulo. O resumo precisa priorizar volume/nuvens.
        "weather_code": 63,
        "temperature_min": 20.4,
        "temperature_max": 29.2,
        "rain_probability_max": 80,
        "rain_probability_mean": 12,
        "rain_sum": 0.0,
        "rain_hours": 0,
        "cloud_cover_mean": 40,
        "wind_max": 19.6,
    }

    text = format_forecast(location, forecast, heading="Tempo amanhã")

    assert "Tempo amanhã — Cruz das Almas - BA" in text
    assert "20–29 °C" in text
    assert "sol entre nuvens" in text
    assert "Chuva prevista: 0.0 mm" in text
    assert "80%" not in text
    assert "Fonte: Open-Meteo" in text


def test_format_forecast_with_relevant_rain_shows_mean_and_hourly_peak():
    location = {"city": "Cruz das Almas - BA"}
    forecast = {
        "weather_code": 63,
        "temperature_min": 21.4,
        "temperature_max": 28.2,
        "rain_probability_max": 80,
        "rain_probability_mean": 42,
        "rain_sum": 7.3,
        "rain_hours": 4,
        "cloud_cover_mean": 75,
        "wind_max": 19.6,
    }

    text = format_forecast(location, forecast, heading="Tempo amanhã")

    assert "chuva moderada em alguns períodos" in text
    assert "21–28 °C" in text
    assert "Chuva prevista: 7.3 mm em ~4 h" in text
    assert "Chance média de chuva: 42% · pico horário: 80%" in text
    assert "Vento: até 20 km/h" in text
