from weather_personality import forecast_comment


def _forecast(**overrides):
    base = {
        "date": "2026-08-31",
        "weather_code": 0,
        "temperature_min": 22,
        "temperature_max": 28,
        "rain_sum": 0,
        "rain_hours": 0,
        "cloud_cover_mean": 30,
        "wind_max": 12,
    }
    base.update(overrides)
    return base


def test_very_hot_day_gets_heat_advice():
    text = forecast_comment(
        _forecast(temperature_max=35, cloud_cover_mean=15),
        heading="Tempo hoje",
        city="Cruz das Almas - Bahia",
    )
    assert text.startswith("Hoje")
    assert any(word in text.lower() for word in ("água", "hidrata", "sombra"))


def test_rainy_day_gets_protection_advice():
    text = forecast_comment(
        _forecast(weather_code=63, rain_sum=8.2, rain_hours=5, cloud_cover_mean=85),
        heading="Tempo amanhã",
        city="Cruz das Almas - Bahia",
    )
    assert text.startswith("Amanhã")
    assert any(word in text.lower() for word in ("chuva", "guarda-chuva", "proteção", "prevenido"))


def test_storm_has_priority_over_heat():
    text = forecast_comment(
        _forecast(weather_code=95, temperature_max=35, rain_sum=18, rain_hours=4),
        heading="Tempo hoje",
        city="Cruz das Almas - Bahia",
    )
    assert any(word in text.lower() for word in ("chuva", "guarda-chuva", "molhada"))
    assert "hidrata" not in text.lower()


def test_same_forecast_keeps_same_phrase():
    forecast = _forecast(temperature_max=34, cloud_cover_mean=10)
    first = forecast_comment(forecast, heading="Tempo hoje", city="Cruz das Almas - Bahia")
    second = forecast_comment(forecast, heading="Tempo hoje", city="Cruz das Almas - Bahia")
    assert first == second


def test_different_days_can_rotate_variant_without_randomness():
    variants = {
        forecast_comment(
            _forecast(date=f"2026-09-{day:02d}", temperature_max=34, cloud_cover_mean=10),
            heading="Tempo hoje",
            city="Cruz das Almas - Bahia",
        )
        for day in range(1, 8)
    }
    assert len(variants) >= 2
