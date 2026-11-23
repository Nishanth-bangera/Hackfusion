import httpx


def get_weather(lat: float, lon: float) -> dict:
    """Fetch current weather and a three-day precipitation/wind outlook."""
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,wind_speed_10m,precipitation",
            "daily": "precipitation_sum,wind_speed_10m_max",
            "forecast_days": 3,
            "timezone": "auto",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
