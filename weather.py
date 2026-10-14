import requests

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def get_coordinates(city):
    """Return (lat, lon) for a city name."""
    r = requests.get(GEO_URL, params={"name": city, "count": 1, "language": "de"}, timeout=10)
    r.raise_for_status()
    results = r.json().get("results")
    if not results:
        return None
    return results[0]["latitude"], results[0]["longitude"]


def get_weather(city, days=3):
    """Return a daily forecast for a city."""
    coords = get_coordinates(city)
    if coords is None:
        return []
    lat, lon = coords
    r = requests.get(WEATHER_URL, params={
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Europe/Berlin",
        "forecast_days": days,
    }, timeout=10)
    r.raise_for_status()
    d = r.json()["daily"]
    return [
        {
            "date": d["time"][i],
            "max_c": d["temperature_2m_max"][i],
            "min_c": d["temperature_2m_min"][i],
            "rain_chance": d["precipitation_probability_max"][i],
        }
        for i in range(len(d["time"]))
    ]


if __name__ == "__main__":
    for city in ["Berlin", "München", "Hamburg"]:
        print(f"\n{city}")
        for day in get_weather(city):
            print(f"  {day['date']}  {day['min_c']}–{day['max_c']} °C  rain {day['rain_chance']}%")
