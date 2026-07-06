import requests

from app.services.context_data import UrbanContextService


def enabled_service() -> UrbanContextService:
    service = UrbanContextService()
    service.enabled = True
    service.weather_key = "test-key"
    return service


def test_context_is_empty_when_disabled() -> None:
    service = UrbanContextService()
    service.enabled = False

    assert service.get_context(21.0, 105.8) == {}


def test_context_is_empty_without_coordinates() -> None:
    service = enabled_service()

    assert service.get_context(None, 105.8) == {}
    assert service.get_context(21.0, None) == {}


def test_weather_timeout_degrades_only_weather(monkeypatch) -> None:
    service = enabled_service()

    def fake_get(url, **_kwargs):
        if "openweathermap" in url:
            raise requests.Timeout("weather timeout")
        return FakeResponse(
            payload={"display_name": "Hanoi", "address": {"city": "Hanoi"}}
        )

    monkeypatch.setattr("app.services.context_data.requests.get", fake_get)

    context = service.get_context(21.0, 105.8)

    assert context["weather"] == {
        "available": False,
        "reason": "request_failed",
    }
    assert context["place"]["available"] is True


def test_nominatim_timeout_degrades_only_place(monkeypatch) -> None:
    service = enabled_service()

    def fake_get(url, **_kwargs):
        if "nominatim" in url:
            raise requests.ConnectionError("map unavailable")
        return FakeResponse(
            payload={
                "weather": [{"main": "Rain", "description": "light rain"}],
                "main": {"temp": 28, "humidity": 90},
                "wind": {"speed": 3},
            }
        )

    monkeypatch.setattr("app.services.context_data.requests.get", fake_get)

    context = service.get_context(21.0, 105.8)

    assert context["weather"]["available"] is True
    assert context["place"] == {
        "available": False,
        "reason": "request_failed",
    }


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload = payload or {}
        self.status_code = status_code
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload
