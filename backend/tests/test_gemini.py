import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.services.gemini import GeminiAnalyzer


VALID_ANALYSIS = {
    "category": "flooding",
    "severity": 4,
    "confidence": 0.86,
    "summary": "Flood water is obstructing a residential street.",
    "recommendation": "Inspect drainage and restrict access if water rises.",
    "priority": "high",
    "estimated_impact": "Residents and road users may be affected.",
    "evidence": ["Citizen reports rising flood water."],
    "uncertainty": ["Water depth is not independently verified."],
}


def analyzer_with_response(text):
    calls = {}

    def generate_content(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(text=text)

    analyzer = GeminiAnalyzer.__new__(GeminiAnalyzer)
    analyzer.model = "test-model"
    analyzer.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    return analyzer, calls


def test_gemini_valid_json_returns_structured_analysis() -> None:
    analyzer, calls = analyzer_with_response(json.dumps(VALID_ANALYSIS))

    result = analyzer.analyze("Flooding reported", b"image", "image/jpeg")

    assert result.category == "flooding"
    assert result.severity == 4
    assert calls["model"] == "test-model"
    assert calls["config"].response_mime_type == "application/json"


def test_gemini_invalid_schema_is_rejected() -> None:
    invalid = {**VALID_ANALYSIS, "severity": 9}
    analyzer, _ = analyzer_with_response(json.dumps(invalid))

    with pytest.raises(ValidationError):
        analyzer.analyze("Flooding reported", None, None)


def test_gemini_empty_response_is_rejected() -> None:
    analyzer, _ = analyzer_with_response("")

    with pytest.raises(RuntimeError, match="empty response"):
        analyzer.analyze("Flooding reported", None, None)
