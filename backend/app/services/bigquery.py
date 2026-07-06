import json
from datetime import datetime, timezone

from google.cloud import bigquery

from app.config import Settings


class BigQueryReportSink:
    def __init__(self, settings: Settings):
        self.enabled = settings.enable_bigquery
        self.status_table_id = (
            f"{settings.google_cloud_project}."
            f"{settings.bigquery_dataset}.report_status_events"
        )
        self.table_id = (
            f"{settings.google_cloud_project}."
            f"{settings.bigquery_dataset}.{settings.bigquery_reports_table}"
        )
        self.client = (
            bigquery.Client(project=settings.google_cloud_project)
            if self.enabled
            else None
        )

    def list_recent(
        self,
        limit: int = 20,
        status: str | None = None,
        category: str | None = None,
        priority: str | None = None,
        min_severity: int | None = None,
        max_severity: int | None = None,
    ) -> list[dict]:
        if not self.enabled or self.client is None:
            return []

        query = f"""
        WITH latest_status AS (
            SELECT report_id, status, note, created_at
            FROM `{self.status_table_id}`
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY report_id ORDER BY created_at DESC
            ) = 1
        )
        SELECT
            r.report_id, r.urban_context, r.created_at, r.image_gcs_uri,
            r.description, r.latitude, r.longitude, r.category, r.severity,
            r.confidence, r.summary, r.recommendation, r.priority,
            r.estimated_impact, r.evidence, r.uncertainty,
            COALESCE(s.status, 'new') AS status,
            s.note AS status_note
        FROM `{self.table_id}` r
        LEFT JOIN latest_status s USING(report_id)
        WHERE (@status IS NULL OR COALESCE(s.status, 'new') = @status)
          AND (@category IS NULL OR r.category = @category)
          AND (@priority IS NULL OR r.priority = @priority)
          AND (@min_severity IS NULL OR r.severity >= @min_severity)
          AND (@max_severity IS NULL OR r.severity <= @max_severity)
        ORDER BY r.created_at DESC
        LIMIT @limit
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
                bigquery.ScalarQueryParameter("status", "STRING", status),
                bigquery.ScalarQueryParameter("category", "STRING", category),
                bigquery.ScalarQueryParameter("priority", "STRING", priority),
                bigquery.ScalarQueryParameter(
                    "min_severity", "INT64", min_severity
                ),
                bigquery.ScalarQueryParameter(
                    "max_severity", "INT64", max_severity
                ),
            ]
        )
        rows = self.client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]

    def insert(
        self,
        report_id,
        description,
        latitude,
        longitude,
        analysis,
        urban_context=None,
        image_gcs_uri: str | None = None,
    ) -> bool:
        if not self.enabled or self.client is None:
            return False

        row = {
            "report_id": report_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "description": description,
            "latitude": latitude,
            "longitude": longitude,
            "urban_context": json.dumps(urban_context or {}, ensure_ascii=False),
            "image_gcs_uri": image_gcs_uri,
            **analysis.model_dump(mode="json"),
        }
        errors = self.client.insert_rows_json(
            self.table_id, [row], row_ids=[report_id]
        )
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")
        return True

    def summary(self) -> dict:
        if not self.enabled or self.client is None:
            return {
                "total_reports": 0,
                "critical_reports": 0,
                "avg_severity": 0,
                "top_category": "none",
            }

        query = f"""
        WITH base AS (
            SELECT category, severity, priority
            FROM `{self.table_id}`
        ),
        cat AS (
            SELECT category, COUNT(*) AS n
            FROM base
            GROUP BY category
            ORDER BY n DESC
            LIMIT 1
        )
        SELECT
            COUNT(1) AS total_reports,
            COUNTIF(priority = 'critical') AS critical_reports,
            COALESCE(ROUND(AVG(severity), 2), 0) AS avg_severity,
            COALESCE((SELECT category FROM cat), 'none') AS top_category
        FROM base
        """
        row = list(self.client.query(query).result())[0]
        return dict(row)

    def update_status(
        self, report_id: str, status: str, note: str | None = None
    ) -> bool:
        if not self.enabled or self.client is None:
            return False

        row = {
            "report_id": report_id,
            "status": status,
            "note": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        errors = self.client.insert_rows_json(self.status_table_id, [row])
        if errors:
            raise RuntimeError(f"BigQuery status insert failed: {errors}")
        return True

    def get_image_gcs_uri(self, report_id: str) -> str | None:
        if not self.enabled or self.client is None:
            return None

        query = f"""
        SELECT image_gcs_uri
        FROM `{self.table_id}`
        WHERE report_id = @report_id
        LIMIT 1
        """
        job_config = self._report_id_job_config(report_id)
        rows = list(self.client.query(query, job_config=job_config).result())
        return rows[0].get("image_gcs_uri") if rows else None

    def get_report(self, report_id: str) -> dict | None:
        if not self.enabled or self.client is None:
            return None

        query = f"""
        WITH latest_status AS (
            SELECT report_id, status, note, created_at
            FROM `{self.status_table_id}`
            WHERE report_id = @report_id
            QUALIFY ROW_NUMBER() OVER (ORDER BY created_at DESC) = 1
        )
        SELECT
            r.*,
            COALESCE(s.status, 'new') AS status,
            s.note AS status_note,
            s.created_at AS status_updated_at
        FROM `{self.table_id}` r
        LEFT JOIN latest_status s USING(report_id)
        WHERE r.report_id = @report_id
        LIMIT 1
        """
        job_config = self._report_id_job_config(report_id)
        rows = list(self.client.query(query, job_config=job_config).result())
        return dict(rows[0]) if rows else None

    def status_history(self, report_id: str) -> list[dict]:
        if not self.enabled or self.client is None:
            return []

        query = f"""
        SELECT status, note, created_at
        FROM `{self.status_table_id}`
        WHERE report_id = @report_id
        ORDER BY created_at DESC
        """
        job_config = self._report_id_job_config(report_id)
        rows = self.client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]

    @staticmethod
    def _report_id_job_config(report_id: str) -> bigquery.QueryJobConfig:
        return bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "report_id", "STRING", report_id
                )
            ]
        )
