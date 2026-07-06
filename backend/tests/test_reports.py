from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import reports as reports_api
from app.config import Settings
from app.main import app
from app.services.bigquery import BigQueryReportSink


client = TestClient(app)


def test_bigquery_sink_read_methods_are_safe_when_disabled() -> None:
    sink = BigQueryReportSink(Settings(enable_bigquery=False))

    assert sink.get_report("report-1") is None
    assert sink.status_history("report-1") == []
    assert sink.get_image_gcs_uri("report-1") is None


def test_report_detail_returns_report(monkeypatch) -> None:
    sink = SimpleNamespace(
        get_report=lambda report_id: {
            "report_id": report_id,
            "status": "reviewing",
            "urban_context": "{}",
        }
    )
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)

    response = client.get("/api/v1/reports/report-1")

    assert response.status_code == 200
    assert response.json()["status"] == "reviewing"


def test_report_detail_returns_404_when_missing(monkeypatch) -> None:
    sink = SimpleNamespace(get_report=lambda _report_id: None)
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)

    response = client.get("/api/v1/reports/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"


def test_status_history_returns_items_and_count(monkeypatch) -> None:
    events = [
        {
            "status": "reviewing",
            "note": "Assigned to field team",
            "created_at": "2026-07-06T10:00:00+00:00",
        }
    ]
    sink = SimpleNamespace(
        get_report=lambda report_id: {"report_id": report_id},
        status_history=lambda _report_id: events,
    )
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)

    response = client.get("/api/v1/reports/report-1/status-history")

    assert response.status_code == 200
    assert response.json() == {"items": events, "count": 1}


def test_status_history_does_not_return_orphan_events(monkeypatch) -> None:
    sink = SimpleNamespace(
        get_report=lambda _report_id: None,
        status_history=lambda _report_id: [],
    )
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)

    response = client.get("/api/v1/reports/missing/status-history")

    assert response.status_code == 404


def test_status_update_requires_existing_report(monkeypatch) -> None:
    sink = SimpleNamespace(
        get_report=lambda _report_id: None,
        update_status=lambda *_args: True,
    )
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)

    response = client.patch(
        "/api/v1/reports/missing/status", params={"status": "reviewing"}
    )

    assert response.status_code == 404


def test_status_update_appends_event(monkeypatch) -> None:
    calls = []
    sink = SimpleNamespace(
        get_report=lambda report_id: {"report_id": report_id},
        update_status=lambda report_id, status, note: calls.append(
            (report_id, status, note)
        )
        or True,
    )
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)

    response = client.patch(
        "/api/v1/reports/report-1/status",
        params={"status": "resolved", "note": "Work completed"},
    )

    assert response.status_code == 200
    assert response.json()["updated"] is True
    assert calls == [("report-1", "resolved", "Work completed")]


def test_report_query_failure_returns_clear_502(monkeypatch) -> None:
    def fail(_report_id):
        raise RuntimeError("warehouse unavailable")

    monkeypatch.setattr(
        reports_api,
        "get_sink",
        lambda: SimpleNamespace(get_report=fail),
    )

    response = client.get("/api/v1/reports/report-1")

    assert response.status_code == 502
    assert "Report query failed" in response.json()["detail"]


@pytest.mark.parametrize("limit", [0, 101])
def test_recent_limit_must_be_bounded(limit) -> None:
    response = client.get("/api/v1/reports/recent", params={"limit": limit})

    assert response.status_code == 422
    assert "between 1 and 100" in response.json()["detail"]


def test_recent_query_failure_returns_502(monkeypatch) -> None:
    def fail(_limit):
        raise RuntimeError("warehouse unavailable")

    monkeypatch.setattr(
        reports_api,
        "get_sink",
        lambda: SimpleNamespace(list_recent=fail),
    )

    response = client.get("/api/v1/reports/recent")

    assert response.status_code == 502
    assert "BigQuery query failed" in response.json()["detail"]


def test_recent_filters_are_forwarded_to_sink(monkeypatch) -> None:
    calls = {}

    class Sink:
        def list_recent(self, limit, **filters):
            calls["limit"] = limit
            calls["filters"] = filters
            return [{"report_id": "report-1"}]

    monkeypatch.setattr(reports_api, "get_sink", lambda: Sink())

    response = client.get(
        "/api/v1/reports/recent",
        params={
            "limit": 30,
            "status": "reviewing",
            "category": "flooding",
            "priority": "high",
            "min_severity": 3,
            "max_severity": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert calls == {
        "limit": 30,
        "filters": {
            "status": "reviewing",
            "category": "flooding",
            "priority": "high",
            "min_severity": 3,
            "max_severity": 5,
        },
    }


@pytest.mark.parametrize(
    ("name", "value", "detail"),
    [
        ("status", "unknown", "Invalid status filter"),
        ("category", "traffic", "Invalid category filter"),
        ("priority", "urgent", "Invalid priority filter"),
    ],
)
def test_recent_rejects_invalid_enum_filters(name, value, detail) -> None:
    response = client.get("/api/v1/reports/recent", params={name: value})

    assert response.status_code == 422
    assert response.json()["detail"] == detail


def test_recent_rejects_inverted_severity_range() -> None:
    response = client.get(
        "/api/v1/reports/recent",
        params={"min_severity": 5, "max_severity": 2},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "min_severity cannot exceed max_severity"


def test_summary_query_failure_returns_502(monkeypatch) -> None:
    def fail():
        raise RuntimeError("warehouse unavailable")

    monkeypatch.setattr(
        reports_api,
        "get_sink",
        lambda: SimpleNamespace(summary=fail),
    )

    response = client.get("/api/v1/reports/summary")

    assert response.status_code == 502
    assert "BigQuery summary failed" in response.json()["detail"]


def test_invalid_status_returns_422() -> None:
    response = client.patch(
        "/api/v1/reports/report-1/status",
        params={"status": "in-progress"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid status"


def test_status_update_failure_returns_502(monkeypatch) -> None:
    def fail(*_args):
        raise RuntimeError("status table unavailable")

    sink = SimpleNamespace(
        get_report=lambda report_id: {"report_id": report_id},
        update_status=fail,
    )
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)

    response = client.patch(
        "/api/v1/reports/report-1/status",
        params={"status": "reviewing"},
    )

    assert response.status_code == 502
    assert "Status update failed" in response.json()["detail"]


def test_status_history_failure_returns_502(monkeypatch) -> None:
    def fail(_report_id):
        raise RuntimeError("history unavailable")

    sink = SimpleNamespace(
        get_report=lambda report_id: {"report_id": report_id},
        status_history=fail,
    )
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)

    response = client.get("/api/v1/reports/report-1/status-history")

    assert response.status_code == 502
    assert "Status history query failed" in response.json()["detail"]


def test_image_proxy_returns_private_image(monkeypatch) -> None:
    sink = SimpleNamespace(
        get_image_gcs_uri=lambda _report_id: "gs://private-bucket/report.jpg"
    )
    storage = SimpleNamespace(
        download_by_gcs_uri=lambda _uri: (b"private-image", "image/jpeg")
    )
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)
    monkeypatch.setattr(reports_api, "get_evidence_storage", lambda: storage)

    response = client.get("/api/v1/reports/report-1/image")

    assert response.status_code == 200
    assert response.content == b"private-image"
    assert response.headers["content-type"] == "image/jpeg"


def test_image_proxy_returns_404_when_report_has_no_image(monkeypatch) -> None:
    sink = SimpleNamespace(get_image_gcs_uri=lambda _report_id: None)
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)

    response = client.get("/api/v1/reports/report-1/image")

    assert response.status_code == 404
    assert response.json()["detail"] == "No image found for this report"


def test_image_proxy_returns_502_when_gcs_fails(monkeypatch) -> None:
    def fail(_uri):
        raise RuntimeError("GCS unavailable")

    sink = SimpleNamespace(
        get_image_gcs_uri=lambda _report_id: "gs://private-bucket/report.jpg"
    )
    storage = SimpleNamespace(download_by_gcs_uri=fail)
    monkeypatch.setattr(reports_api, "get_sink", lambda: sink)
    monkeypatch.setattr(reports_api, "get_evidence_storage", lambda: storage)

    response = client.get("/api/v1/reports/report-1/image")

    assert response.status_code == 502
    assert "Image fetch failed" in response.json()["detail"]
