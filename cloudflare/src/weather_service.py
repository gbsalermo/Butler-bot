"""Serviço meteorológico do Butler usando Open-Meteo.

Sem chave de API. O runtime de produção roda em Pyodide, então as chamadas HTTP
usam ``js.fetch`` como a integração com Telegram já faz.
"""

import json
from datetime import date
from urllib.parse import quote_plus

from js import fetch

from settings import (
    DEFAULT_WEATHER_CITY,
    DEFAULT_WEATHER_LATITUDE,
    DEFAULT_WEATHER_LONGITUDE,
    TIMEZONE_NAME,
)
from weather_personality import forecast_comment

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: ("☀️", "céu limpo"),
    1: ("🌤️", "predominantemente limpo"),
    2: ("⛅", "parcialmente nublado"),
    3: ("☁️", "nublado"),
    45: ("🌫️", "neblina"),
    48: ("🌫️", "neblina com geada"),
    51: ("🌦️", "garoa fraca"),
    53: ("🌦️", "garoa moderada"),
    55: ("🌧️", "garoa forte"),
    61: ("🌦️", "chuva fraca"),
    63: ("🌧️", "chuva moderada"),
    65: ("🌧️", "chuva forte"),
    80: ("🌦️", "pancadas de chuva fracas"),
    81: ("🌧️", "pancadas de chuva"),
    82: ("⛈️", "pancadas fortes"),
    95: ("⛈️", "trovoadas"),
    96: ("⛈️", "trovoadas com granizo"),
    99: ("⛈️", "trovoadas fortes com granizo"),
}


def _row(row, key, default=None):
    if row is None:
        return default
    try:
        return getattr(row, key)
    except Exception:
        try:
            return row[key]
        except Exception:
            return default


def _number(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


async def _get_json(url):
    response = await fetch(url)
    if not response.ok:
        raise RuntimeError(f"HTTP {int(response.status)}")
    text = await response.text()
    return json.loads(text)


async def ensure_schema(db):
    await db.prepare(
        """
        CREATE TABLE IF NOT EXISTS weather_preferences (
            user_id INTEGER PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 1,
            morning_enabled INTEGER NOT NULL DEFAULT 1,
            city TEXT,
            latitude REAL,
            longitude REAL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    ).run()


async def get_location(db, uid):
    await ensure_schema(db)
    pref = await db.prepare(
        "SELECT enabled,morning_enabled,city,latitude,longitude FROM weather_preferences WHERE user_id=?"
    ).bind(uid).first()

    if pref and int(_row(pref, "enabled", 1)):
        lat = _row(pref, "latitude")
        lon = _row(pref, "longitude")
        if lat is not None and lon is not None:
            return {
                "city": _row(pref, "city") or "local configurado",
                "latitude": float(lat),
                "longitude": float(lon),
                "morning_enabled": bool(int(_row(pref, "morning_enabled", 1))),
            }

    owner = await db.prepare("SELECT COALESCE(is_owner,0) is_owner FROM users WHERE id=?").bind(uid).first()
    if owner and int(_row(owner, "is_owner", 0)):
        return {
            "city": DEFAULT_WEATHER_CITY,
            "latitude": float(DEFAULT_WEATHER_LATITUDE),
            "longitude": float(DEFAULT_WEATHER_LONGITUDE),
            "morning_enabled": True,
        }
    return None


async def geocode_city(city):
    query = quote_plus((city or "").strip())
    if not query:
        raise ValueError("cidade vazia")
    data = await _get_json(f"{GEOCODING_URL}?name={query}&count=8&language=pt&format=json")
    results = data.get("results") or []
    if not results:
        raise ValueError("cidade não encontrada")

    chosen = next((item for item in results if item.get("country_code") == "BR"), results[0])
    name = chosen.get("name") or city.strip()
    admin = chosen.get("admin1")
    country = chosen.get("country")
    label = name
    if admin and admin.lower() not in label.lower():
        label += f" - {admin}"
    if country and country.lower() not in label.lower() and chosen.get("country_code") != "BR":
        label += f", {country}"
    return {
        "city": label,
        "latitude": float(chosen["latitude"]),
        "longitude": float(chosen["longitude"]),
    }


async def set_city(db, uid, city):
    await ensure_schema(db)
    location = await geocode_city(city)
    await db.prepare(
        """
        INSERT INTO weather_preferences(user_id,enabled,morning_enabled,city,latitude,longitude,updated_at)
        VALUES(?,1,1,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            enabled=1,
            city=excluded.city,
            latitude=excluded.latitude,
            longitude=excluded.longitude,
            updated_at=CURRENT_TIMESTAMP
        """
    ).bind(uid, location["city"], location["latitude"], location["longitude"]).run()
    return location


async def set_morning_enabled(db, uid, enabled):
    await ensure_schema(db)
    current = await get_location(db, uid)
    if not current:
        return False
    await db.prepare(
        """
        INSERT INTO weather_preferences(user_id,enabled,morning_enabled,city,latitude,longitude,updated_at)
        VALUES(?,1,?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET morning_enabled=excluded.morning_enabled,updated_at=CURRENT_TIMESTAMP
        """
    ).bind(
        uid,
        1 if enabled else 0,
        current["city"],
        current["latitude"],
        current["longitude"],
    ).run()
    return True


async def fetch_daily_forecast(location, target):
    if isinstance(target, str):
        target = date.fromisoformat(target)
    day = target.isoformat()
    params = (
        f"latitude={location['latitude']}&longitude={location['longitude']}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,precipitation_probability_mean,"
        "precipitation_sum,precipitation_hours,cloud_cover_mean,wind_speed_10m_max"
        f"&timezone={quote_plus(TIMEZONE_NAME)}&start_date={day}&end_date={day}"
    )
    data = await _get_json(f"{FORECAST_URL}?{params}")
    daily = data.get("daily") or {}
    times = daily.get("time") or []
    if not times:
        raise ValueError("previsão indisponível")

    def first(name, default=None):
        values = daily.get(name) or []
        return values[0] if values else default

    return {
        "date": times[0],
        "weather_code": int(first("weather_code", -1)),
        "temperature_max": first("temperature_2m_max"),
        "temperature_min": first("temperature_2m_min"),
        "rain_probability_max": first("precipitation_probability_max"),
        "rain_probability_mean": first("precipitation_probability_mean"),
        "rain_sum": first("precipitation_sum"),
        "rain_hours": first("precipitation_hours"),
        "cloud_cover_mean": first("cloud_cover_mean"),
        "wind_max": first("wind_speed_10m_max"),
    }


def _day_condition(forecast):
    """Resume o dia sem deixar o WMO 'mais severo do dia' dominar a mensagem."""
    rain_sum = _number(forecast.get("rain_sum"))
    rain_hours = _number(forecast.get("rain_hours"))
    cloud = _number(forecast.get("cloud_cover_mean"))

    if rain_sum is not None and rain_sum <= 0.1:
        if cloud is None:
            code = forecast.get("weather_code")
            icon, condition = WEATHER_CODES.get(code, ("🌤️", "condição variável"))
            if code in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}:
                return "🌤️", "sem chuva relevante prevista"
            return icon, condition
        if cloud <= 25:
            return "☀️", "predomínio de sol"
        if cloud <= 65:
            return "🌤️", "sol entre nuvens"
        return "☁️", "muitas nuvens"

    if rain_sum is not None:
        if rain_sum < 1.0:
            return "🌦️", "baixa possibilidade de chuva passageira"
        if rain_hours is not None and rain_hours <= 2:
            return "🌦️", "chuva passageira em algum período"
        if rain_sum < 5.0:
            return "🌦️", "chuva fraca em alguns períodos"
        if rain_sum < 15.0:
            return "🌧️", "chuva moderada em alguns períodos"
        return "⛈️", "chuva forte em alguns períodos"

    return WEATHER_CODES.get(forecast.get("weather_code"), ("🌤️", "condição variável"))


def format_forecast(location, forecast, heading="Tempo"):
    icon, condition = _day_condition(forecast)
    tmin = _number(forecast.get("temperature_min"))
    tmax = _number(forecast.get("temperature_max"))
    rain_max = _number(forecast.get("rain_probability_max"))
    rain_mean = _number(forecast.get("rain_probability_mean"))
    rain_sum = _number(forecast.get("rain_sum"))
    rain_hours = _number(forecast.get("rain_hours"))
    wind = _number(forecast.get("wind_max"))

    lines = [
        f"{icon} {heading} — {location['city']}",
        forecast_comment(forecast, heading=heading, city=location["city"]),
    ]
    if tmin is not None and tmax is not None:
        lines.append(f"• {condition}; {round(tmin)}–{round(tmax)} °C")

    if rain_sum is not None:
        if rain_sum <= 0.1:
            lines.append(f"• Chuva prevista: {rain_sum:.1f} mm")
        else:
            duration = ""
            if rain_hours is not None:
                duration = f" em ~{round(rain_hours)} h"
            lines.append(f"• Chuva prevista: {rain_sum:.1f} mm{duration}")

    if rain_mean is not None and rain_sum is not None and rain_sum > 0.1:
        if rain_max is not None and rain_max > rain_mean:
            lines.append(f"• Chance de chuva: de {round(rain_mean)}% até {round(rain_max)}%")
        else:
            lines.append(f"• Chance de chuva: {round(rain_mean)}%")
    elif rain_mean is not None and rain_sum is None:
        if rain_max is not None and rain_max > rain_mean:
            lines.append(f"• Chance de chuva: de {round(rain_mean)}% até {round(rain_max)}%")
        else:
            lines.append(f"• Chance de chuva: {round(rain_mean)}%")
    elif rain_max is not None and rain_sum is None:
        lines.append(f"• Chance de chuva: até {round(rain_max)}%")

    if wind is not None:
        lines.append(f"• Vento: até {round(wind)} km/h")
    lines.append("• Fonte: Open-Meteo")
    return "\n".join(lines)


async def forecast_text(db, uid, target, heading="Tempo"):
    location = await get_location(db, uid)
    if not location:
        return None
    forecast = await fetch_daily_forecast(location, target)
    return format_forecast(location, forecast, heading=heading)


async def safe_forecast_text(db, uid, target, heading="Tempo", morning_only=False):
    try:
        location = await get_location(db, uid)
        if not location:
            return None
        if morning_only and not location.get("morning_enabled", True):
            return None
        forecast = await fetch_daily_forecast(location, target)
        return format_forecast(location, forecast, heading=heading)
    except Exception as exc:
        print(f"[weather] forecast-error type={type(exc).__name__} message={str(exc)[:240]}")
        return None
