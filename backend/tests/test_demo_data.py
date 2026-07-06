import json
import struct
from datetime import datetime, timezone

from app.demo_data import (
    REPORTS,
    STATUS_EVENTS,
    build_report_rows,
    build_status_rows,
    demo_evidence_png,
    demo_summary,
)


def test_demo_dataset_meets_acceptance_criteria() -> None:
    summary = demo_summary()

    assert 8 <= summary["reports"] <= 12
    assert summary["images"] >= 1
    assert summary["status_events"] >= 2
    assert summary["urban_context_reports"] >= 1
    assert summary["priorities"]["critical"] >= 1
    assert summary["priorities"]["high"] >= 1
    assert summary["priorities"]["medium"] >= 1
    assert summary["priorities"]["low"] >= 1
    assert len({report.report_id for report in REPORTS}) == len(REPORTS)


def test_demo_rows_are_deterministic_and_schema_ready() -> None:
    now = datetime(2026, 7, 6, 12, tzinfo=timezone.utc)
    rows = build_report_rows(now, image_uri="gs://private/demo.png")

    assert len(rows) == 10
    assert rows[0]["report_id"] == "demo-001-pothole-school"
    assert json.loads(rows[0]["urban_context"])["weather"]["source"] == "synthetic_demo"
    image_rows = [row for row in rows if row["image_gcs_uri"]]
    assert len(image_rows) == 1
    assert image_rows[0]["image_gcs_uri"] == "gs://private/demo.png"
    assert all(row["created_at"] <= now.isoformat() for row in rows)


def test_demo_status_history_is_ordered_after_report_creation() -> None:
    now = datetime(2026, 7, 6, 12, tzinfo=timezone.utc)
    reports = {row["report_id"]: row for row in build_report_rows(now)}
    statuses = build_status_rows(now)

    assert len(statuses) == len(STATUS_EVENTS)
    for status in statuses:
        assert status["created_at"] > reports[status["report_id"]]["created_at"]
    flood_history = [
        row for row in statuses if row["report_id"] == "demo-002-flooded-street"
    ]
    assert [row["status"] for row in flood_history] == ["reviewing", "resolved"]


def test_demo_evidence_is_valid_rgb_png() -> None:
    image = demo_evidence_png()

    assert image.startswith(b"\x89PNG\r\n\x1a\n")
    assert image[12:16] == b"IHDR"
    width, height = struct.unpack(">II", image[16:24])
    assert (width, height) == (320, 180)
