import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")

from app.config import Settings  # noqa: E402
from app.demo_data import (  # noqa: E402
    REPORTS,
    STATUS_EVENTS,
    build_report_rows,
    build_status_rows,
    demo_evidence_png,
    demo_summary,
)
from app.services.storage import EvidenceStorage  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Seed deterministic CityMind demo data.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write missing demo rows to BigQuery and one image to private GCS.",
    )
    return parser.parse_args()


def existing_report_ids(client, table_id, report_ids):
    query = f"""
    SELECT report_id
    FROM `{table_id}`
    WHERE report_id IN UNNEST(@report_ids)
    """
    config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("report_ids", "STRING", report_ids)
        ]
    )
    return {
        row["report_id"]
        for row in client.query(query, job_config=config).result()
    }


def existing_status_keys(client, table_id, report_ids):
    query = f"""
    SELECT report_id, status, note
    FROM `{table_id}`
    WHERE report_id IN UNNEST(@report_ids)
    """
    config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("report_ids", "STRING", report_ids)
        ]
    )
    return {
        (row["report_id"], row["status"], row.get("note"))
        for row in client.query(query, job_config=config).result()
    }


def apply_seed(settings):
    if not settings.enable_bigquery:
        raise RuntimeError("ENABLE_BIGQUERY must be true")
    if not settings.enable_image_storage or not settings.gcs_bucket_name:
        raise RuntimeError("Private image storage must be enabled and configured")

    client = bigquery.Client(project=settings.google_cloud_project)
    reports_table = (
        f"{settings.google_cloud_project}.{settings.bigquery_dataset}."
        f"{settings.bigquery_reports_table}"
    )
    status_table = (
        f"{settings.google_cloud_project}.{settings.bigquery_dataset}."
        "report_status_events"
    )
    report_ids = [report.report_id for report in REPORTS]
    existing_reports = existing_report_ids(client, reports_table, report_ids)
    missing_reports = [r for r in REPORTS if r.report_id not in existing_reports]

    image_report = next(report for report in REPORTS if report.has_image)
    image_uri = None
    if image_report.report_id in {r.report_id for r in missing_reports}:
        image_uri = EvidenceStorage(settings).upload_image(
            image_report.report_id,
            demo_evidence_png(),
            "image/png",
        )

    now = datetime.now(timezone.utc)
    report_rows = [
        row
        for row in build_report_rows(now, image_uri=image_uri)
        if row["report_id"] not in existing_reports
    ]
    if report_rows:
        errors = client.insert_rows_json(
            reports_table,
            report_rows,
            row_ids=[row["report_id"] for row in report_rows],
        )
        if errors:
            raise RuntimeError(f"Demo report insert failed: {errors}")

    existing_statuses = existing_status_keys(client, status_table, report_ids)
    status_rows = [
        row
        for row in build_status_rows(now)
        if (row["report_id"], row["status"], row["note"]) not in existing_statuses
    ]
    if status_rows:
        errors = client.insert_rows_json(
            status_table,
            status_rows,
            row_ids=[
                f"{row['report_id']}-{row['status']}" for row in status_rows
            ],
        )
        if errors:
            raise RuntimeError(f"Demo status insert failed: {errors}")

    return {
        "reports_inserted": len(report_rows),
        "reports_skipped": len(existing_reports),
        "status_events_inserted": len(status_rows),
        "image_uploaded": image_uri is not None,
    }


def main():
    args = parse_args()
    print(json.dumps(demo_summary(), indent=2, sort_keys=True))
    if not args.apply:
        print("Dry run only. Use --apply to write demo data.")
        return 0

    result = apply_seed(Settings())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
