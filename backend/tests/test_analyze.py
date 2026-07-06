from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import reports as reports_api
from app.main import app
from app.schemas import ReportAnalysis
from app.services.context_data import UrbanContextService


client = TestClient(app)


def analysis_result() -> ReportAnalysis:
    return ReportAnalysis(
        category="pothole",
        severity=4,
        confidence=0.82,
        summary="Large pothole near a school entrance.",
        recommendation="Inspect the road and secure the affected lane.",
        priority="high",
        estimated_impact="Safety risk for students and road users.",
        evidence=["Citizen description identifies a large pothole."],
        uncertainty=["Exact dimensions are not verified."],
    )


def install_successful_pipeline(monkeypatch, context=None):
    calls = {}

    class Storage:
        def upload_image(self, report_id, image_bytes, mime_type):
            calls["upload"] = (report_id, image_bytes, mime_type)
            return "gs://private-bucket/reports/evidence.jpg" if image_bytes else None

    class Context:
        def get_context(self, latitude, longitude):
            calls["context_coordinates"] = (latitude, longitude)
            return context or {}

    class Analyzer:
        def analyze(self, description, image_bytes, mime_type):
            calls["analysis_input"] = (description, image_bytes, mime_type)
            return analysis_result()

    class Sink:
        def insert(self, *args, **kwargs):
            calls["insert"] = (args, kwargs)
            return True

    monkeypatch.setattr(reports_api, "get_evidence_storage", lambda: Storage())
    monkeypatch.setattr(reports_api, "get_context_service", lambda: Context())
    monkeypatch.setattr(reports_api, "get_analyzer", lambda: Analyzer())
    monkeypatch.setattr(reports_api, "get_sink", lambda: Sink())
    return calls


def test_analyze_text_report_without_image(monkeypatch) -> None:
    calls = install_successful_pipeline(monkeypatch)

    response = client.post(
        "/api/v1/reports/analyze",
        data={"description": "Large pothole near the school"},
    )

    assert response.status_code == 200
    assert response.json()["persisted"] is True
    assert calls["upload"][1:] == (None, None)
    assert calls["analysis_input"] == (
        "Large pothole near the school",
        None,
        None,
    )


def test_analyze_report_with_image_and_context(monkeypatch) -> None:
    context = {"weather": {"available": True, "condition": "Rain"}}
    calls = install_successful_pipeline(monkeypatch, context=context)

    response = client.post(
        "/api/v1/reports/analyze",
        data={
            "description": "Flooding at the intersection",
            "latitude": "21.0285",
            "longitude": "105.8542",
        },
        files={"image": ("flood.jpg", b"jpeg-data", "image/jpeg")},
    )

    assert response.status_code == 200
    description, image_bytes, mime_type = calls["analysis_input"]
    assert "Flooding at the intersection" in description
    assert "Urban context:" in description
    assert "Rain" in description
    assert image_bytes == b"jpeg-data"
    assert mime_type == "image/jpeg"
    _, insert_kwargs = calls["insert"]
    assert insert_kwargs["urban_context"] == context
    assert insert_kwargs["image_gcs_uri"].startswith("gs://")


def test_empty_image_and_empty_description_are_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        reports_api,
        "get_settings",
        lambda: SimpleNamespace(max_image_bytes=1024),
    )

    response = client.post(
        "/api/v1/reports/analyze",
        data={"description": ""},
        files={"image": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Provide description or image"


def test_unsupported_image_mime_returns_415() -> None:
    response = client.post(
        "/api/v1/reports/analyze",
        data={"description": "Evidence attached"},
        files={"image": ("evidence.txt", b"not-an-image", "text/plain")},
    )

    assert response.status_code == 415
    assert "Only JPEG, PNG, or WebP" in response.json()["detail"]


def test_image_over_limit_returns_413(monkeypatch) -> None:
    monkeypatch.setattr(
        reports_api,
        "get_settings",
        lambda: SimpleNamespace(max_image_bytes=3),
    )

    response = client.post(
        "/api/v1/reports/analyze",
        data={"description": "Evidence attached"},
        files={"image": ("evidence.png", b"1234", "image/png")},
    )

    assert response.status_code == 413


def test_description_over_limit_returns_422() -> None:
    response = client.post(
        "/api/v1/reports/analyze",
        data={"description": "x" * 3001},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", "91"),
        ("latitude", "-91"),
        ("longitude", "181"),
        ("longitude", "-181"),
    ],
)
def test_out_of_range_coordinates_return_422(field, value) -> None:
    response = client.post(
        "/api/v1/reports/analyze",
        data={"description": "Valid report", field: value},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("failing_service", ["storage", "analyzer", "sink"])
def test_critical_service_failure_returns_502(monkeypatch, failing_service) -> None:
    class Storage:
        def upload_image(self, *_args):
            if failing_service == "storage":
                raise RuntimeError("storage unavailable")
            return None

    class Context:
        def get_context(self, *_args):
            return {}

    class Analyzer:
        def analyze(self, *_args):
            if failing_service == "analyzer":
                raise RuntimeError("Gemini unavailable")
            return analysis_result()

    class Sink:
        def insert(self, *_args, **_kwargs):
            if failing_service == "sink":
                raise RuntimeError("BigQuery unavailable")
            return True

    monkeypatch.setattr(reports_api, "get_evidence_storage", lambda: Storage())
    monkeypatch.setattr(reports_api, "get_context_service", lambda: Context())
    monkeypatch.setattr(reports_api, "get_analyzer", lambda: Analyzer())
    monkeypatch.setattr(reports_api, "get_sink", lambda: Sink())

    response = client.post(
        "/api/v1/reports/analyze",
        data={"description": "A valid incident report"},
    )

    assert response.status_code == 502
    assert response.json()["detail"].startswith("Report analysis failed:")


def test_context_timeout_does_not_block_analysis(monkeypatch) -> None:
    service = UrbanContextService()
    service.enabled = True
    service.weather_key = "test-key"
    calls = install_successful_pipeline(monkeypatch)
    monkeypatch.setattr(reports_api, "get_context_service", lambda: service)

    def timeout(*_args, **_kwargs):
        import requests

        raise requests.Timeout("upstream timeout")

    monkeypatch.setattr("app.services.context_data.requests.get", timeout)

    response = client.post(
        "/api/v1/reports/analyze",
        data={
            "description": "Blocked drain after rain",
            "latitude": "21.0",
            "longitude": "105.8",
        },
    )

    assert response.status_code == 200
    description, _, _ = calls["analysis_input"]
    assert description.count("request_failed") == 2
    _, insert_kwargs = calls["insert"]
    assert insert_kwargs["urban_context"]["weather"]["available"] is False
    assert insert_kwargs["urban_context"]["place"]["available"] is False
