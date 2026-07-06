import os

import requests


class UrbanContextService:
    def __init__(self):
        self.enabled = os.getenv("ENABLE_URBAN_CONTEXT", "false").lower() == "true"
        self.weather_key = os.getenv("OPENWEATHER_API_KEY")

    def get_context(self, latitude: float | None, longitude: float | None) -> dict:
        if not self.enabled or latitude is None or longitude is None:
            return {}

        return {
            "weather": self._weather(latitude, longitude),
            "place": self._reverse_geocode(latitude, longitude),
        }

    def _weather(self, lat: float, lon: float) -> dict:
        if not self.weather_key:
            return {"available": False, "reason": "missing_openweather_key"}

        url = "https://api.openweathermap.org/data/2.5/weather"
        try:
            res = requests.get(
                url,
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.weather_key,
                    "units": "metric",
                },
                timeout=8,
            )
        except requests.RequestException:
            return {"available": False, "reason": "request_failed"}

        if not res.ok:
            return {"available": False, "status": res.status_code, "body": res.text[:200]}

        data = res.json()
        return {
            "available": True,
            "condition": data.get("weather", [{}])[0].get("main"),
            "description": data.get("weather", [{}])[0].get("description"),
            "temperature_c": data.get("main", {}).get("temp"),
            "humidity": data.get("main", {}).get("humidity"),
            "wind_speed": data.get("wind", {}).get("speed"),
            "rain_1h": data.get("rain", {}).get("1h", 0),
        }

    def _reverse_geocode(self, lat: float, lon: float) -> dict:
        try:
            res = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "format": "jsonv2",
                    "lat": lat,
                    "lon": lon,
                    "addressdetails": 1,
                },
                headers={"User-Agent": "CityMindAI/0.1 demo contact: local"},
                timeout=8,
            )
        except requests.RequestException:
            return {"available": False, "reason": "request_failed"}

        if not res.ok:
            return {"available": False, "status": res.status_code}

        data = res.json()
        return {
            "available": True,
            "display_name": data.get("display_name"),
            "category": data.get("category"),
            "type": data.get("type"),
            "address": data.get("address", {}),
        }
