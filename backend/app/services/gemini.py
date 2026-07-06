import json
from google import genai
from google.genai import types

from app.config import Settings
from app.schemas import ReportAnalysis

SYSTEM_INSTRUCTION = """You analyze urban incident reports for triage support.
Return evidence-based output only. Do not invent facts not visible in the image or text.
Severity scale: 1 cosmetic, 2 minor, 3 service disruption, 4 safety risk, 5 immediate danger.
Priority must reflect severity, affected people, urgency, and uncertainty.
When evidence is insufficient, lower confidence and state uncertainty.
This is decision support, not an autonomous final decision."""


class GeminiAnalyzer:
    def __init__(self, settings: Settings):
        if not settings.google_cloud_project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required")
        self.model = settings.gemini_model
        self.client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )

    def analyze(self, description: str, image: bytes | None, mime_type: str | None) -> ReportAnalysis:
        parts: list[types.Part] = [
            types.Part.from_text(text=f"Citizen description:\n{description or '[none]'}")
        ]
        if image:
            parts.append(types.Part.from_bytes(data=image, mime_type=mime_type or "image/jpeg"))

        response = self.client.models.generate_content(
            model=self.model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=ReportAnalysis,
            ),
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response")
        return ReportAnalysis.model_validate(json.loads(response.text))
