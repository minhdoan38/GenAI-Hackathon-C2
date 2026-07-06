from app.config import Settings
from app.services.bigquery import BigQueryReportSink


class FakeJob:
    def __init__(self, rows):
        self.rows = rows

    def result(self):
        return self.rows


class FakeClient:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.queries = []
        self.inserts = []

    def query(self, query, job_config=None):
        self.queries.append((query, job_config))
        return FakeJob(self.rows)

    def insert_rows_json(self, table, rows, row_ids=None):
        self.inserts.append((table, rows, row_ids))
        return []


def enabled_sink(client) -> BigQueryReportSink:
    sink = BigQueryReportSink(Settings(enable_bigquery=False))
    sink.enabled = True
    sink.client = client
    return sink


def query_parameter(job_config, name):
    return next(param for param in job_config.query_parameters if param.name == name)


def test_recent_query_uses_bounded_parameterized_limit() -> None:
    client = FakeClient(rows=[{"report_id": "report-1"}])
    sink = enabled_sink(client)

    assert sink.list_recent(25) == [{"report_id": "report-1"}]

    query, job_config = client.queries[0]
    assert "LIMIT @limit" in query
    assert query_parameter(job_config, "limit").value == 25


def test_recent_query_parameterizes_all_filters() -> None:
    client = FakeClient(rows=[])
    sink = enabled_sink(client)

    sink.list_recent(
        20,
        status="reviewing",
        category="flooding",
        priority="high",
        min_severity=3,
        max_severity=5,
    )

    query, job_config = client.queries[0]
    assert "COALESCE(s.status, 'new') = @status" in query
    assert "r.category = @category" in query
    assert "r.priority = @priority" in query
    assert "r.severity >= @min_severity" in query
    assert "r.severity <= @max_severity" in query
    assert query_parameter(job_config, "status").value == "reviewing"
    assert query_parameter(job_config, "category").value == "flooding"
    assert query_parameter(job_config, "priority").value == "high"
    assert query_parameter(job_config, "min_severity").value == 3
    assert query_parameter(job_config, "max_severity").value == 5


def test_report_queries_parameterize_report_id() -> None:
    client = FakeClient(rows=[])
    sink = enabled_sink(client)

    sink.get_report("report-unsafe'--")
    sink.get_image_gcs_uri("report-unsafe'--")
    sink.status_history("report-unsafe'--")

    for query, job_config in client.queries:
        assert "@report_id" in query
        assert "report-unsafe'--" not in query
        assert query_parameter(job_config, "report_id").value == "report-unsafe'--"


def test_status_update_is_append_only_insert() -> None:
    client = FakeClient()
    sink = enabled_sink(client)

    assert sink.update_status("report-1", "reviewing", "Assigned") is True

    assert client.queries == []
    table, rows, row_ids = client.inserts[0]
    assert table == sink.status_table_id
    assert rows[0]["report_id"] == "report-1"
    assert rows[0]["status"] == "reviewing"
    assert rows[0]["note"] == "Assigned"
    assert "created_at" in rows[0]
    assert row_ids is None
