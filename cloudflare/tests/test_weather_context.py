from weather_context import _norm
from weather_service import format_forecast


def test_weather_phrase_normalization():
    assert _norm("Previsão do tempo amanhã") == "previsao do tempo amanha"
    assert _norm("Clima em Cruz das Almas, BA") == "clima em cruz das almas ba"


def test_format_forecast_with_rain():
    location = {"city": "Cruz das Almas - BA"}
    forecast = {
        "weather_code": 63,
        "temperature_min": 21.4,
        "temperature_max": 28.2,
        "rain_probability": 80,
        "rain_sum": 7.3,
        "wind_max": 19.6,
    }

    text = format_forecast(location, forecast, heading="Tempo amanhã")

    assert "Tempo amanhã — Cruz das Almas - BA" in text
    assert "21–28 °C" in text
    assert "Chuva: até 80%" in text
    assert "7.3 mm" in text
    assert "Vento: até 20 km/h" in text
