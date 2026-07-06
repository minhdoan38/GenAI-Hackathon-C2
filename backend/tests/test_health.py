from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_report_requires_input() -> None:
    response = client.post("/api/v1/reports/analyze", data={})
    assert response.status_code == 422
