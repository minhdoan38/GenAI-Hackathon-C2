from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import security
from app.api import reports as reports_api
from app.config import Settings
from app.main import app


client = TestClient(app)


def security_settings(key="", app_env="development", limit=0):
    return SimpleNamespace(
        officer_api_key=key,
        app_env=app_env,
        report_rate_limit_per_minute=limit,
    )


def test_protected_endpoint_requires_officer_key(monkeypatch) -> None:
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: security_settings(key="secret", app_env="production"),
    )

    response = client.get("/api/v1/reports/recent")

    assert response.status_code == 401
    assert response.json()["detail"] == "Officer authentication required"


def test_protected_endpoint_accepts_officer_key(monkeypatch) -> None:
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: security_settings(key="secret", app_env="production"),
    )
    monkeypatch.setattr(
        reports_api,
        "get_sink",
        lambda: SimpleNamespace(list_recent=lambda *_args, **_kwargs: []),
    )

    response = client.get(
        "/api/v1/reports/recent",
        headers={"X-CityMind-Officer-Key": "secret"},
    )

    assert response.status_code == 200


def test_production_rejects_missing_auth_configuration(monkeypatch) -> None:
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: security_settings(app_env="production"),
    )

    response = client.get("/api/v1/reports/recent")

    assert response.status_code == 503


def test_sliding_window_limiter_resets_after_window() -> None:
    limiter = security.SlidingWindowLimiter()

    assert limiter.allow("client", limit=2, now=100) is True
    assert limiter.allow("client", limit=2, now=101) is True
    assert limiter.allow("client", limit=2, now=102) is False
    assert limiter.allow("client", limit=2, now=161) is True


def test_report_endpoint_returns_429_after_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: security_settings(limit=1),
    )
    security.report_limiter.clear()
    try:
        first = client.post("/api/v1/reports/analyze", data={})
        second = client.post("/api/v1/reports/analyze", data={})
    finally:
        security.report_limiter.clear()

    assert first.status_code == 422
    assert second.status_code == 429
    assert second.headers["retry-after"] == "60"


def test_cors_origins_are_trimmed_and_normalized() -> None:
    settings = Settings(
        enable_bigquery=False,
        cors_origins="https://one.example/, https://two.example",
    )

    assert settings.cors_origin_list == [
        "https://one.example",
        "https://two.example",
    ]
