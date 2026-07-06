from functools import lru_cache
from typing import Union
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)

from app.config import get_settings
from app.schemas import AnalyzeResponse, Category, Priority
from app.security import enforce_report_rate_limit, require_officer
from app.services.bigquery import BigQueryReportSink
from app.services.context_data import UrbanContextService
from app.services.gemini import GeminiAnalyzer
from app.services.storage import EvidenceStorage

VALID_STATUSES = {"new", "reviewing", "resolved", "rejected"}
VALID_CATEGORIES = {category.value for category in Category}
VALID_PRIORITIES = {priority.value for priority in Priority}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

router = APIRouter()


@lru_cache
def get_analyzer() -> GeminiAnalyzer:
    return GeminiAnalyzer(get_settings())


@lru_cache
def get_sink() -> BigQueryReportSink:
    return BigQueryReportSink(get_settings())


@lru_cache
def get_context_service() -> UrbanContextService:
    return UrbanContextService()


@lru_cache
def get_evidence_storage() -> EvidenceStorage:
    return EvidenceStorage(get_settings())


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_report(
    description: str = Form(default="", max_length=3000),
    latitude: float | None = Form(default=None, ge=-90, le=90),
    longitude: float | None = Form(default=None, ge=-180, le=180),
    image: Union[UploadFile, str, None] = File(default=None),
    _rate_limit: None = Depends(enforce_report_rate_limit),
) -> AnalyzeResponse:
    if isinstance(image, str) or (image is not None and not image.filename):
        image = None

    image_bytes = None
    mime_type = None
    if image is not None:
        mime_type = image.content_type
        image_bytes = await image.read()

        if not image_bytes:
            image_bytes = None
            mime_type = None
        elif mime_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                415,
                f"Only JPEG, PNG, or WebP images are accepted. Received: {mime_type}",
            )
        elif len(image_bytes) > get_settings().max_image_bytes:
            raise HTTPException(413, "Image exceeds configured size limit")

    if not description.strip() and image_bytes is None:
        raise HTTPException(422, "Provide description or image")

    report_id = str(uuid4())
    try:
        image_gcs_uri = get_evidence_storage().upload_image(
            report_id, image_bytes, mime_type
        )
        urban_context = get_context_service().get_context(latitude, longitude)

        enriched_description = description.strip()
        if urban_context:
            enriched_description += f"\n\nUrban context:\n{urban_context}"

        analysis = get_analyzer().analyze(
            enriched_description, image_bytes, mime_type
        )
        persisted = get_sink().insert(
            report_id,
            description.strip(),
            latitude,
            longitude,
            analysis,
            urban_context=urban_context,
            image_gcs_uri=image_gcs_uri,
        )
    except Exception as exc:
        raise HTTPException(502, f"Report analysis failed: {exc}") from exc

    return AnalyzeResponse(
        report_id=report_id,
        analysis=analysis,
        persisted=persisted,
    )


@router.get("/recent")
async def recent_reports(
    limit: int = 20,
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    min_severity: int | None = Query(default=None, ge=1, le=5),
    max_severity: int | None = Query(default=None, ge=1, le=5),
    _officer: None = Depends(require_officer),
):
    if limit < 1 or limit > 100:
        raise HTTPException(422, "limit must be between 1 and 100")
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(422, "Invalid status filter")
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(422, "Invalid category filter")
    if priority is not None and priority not in VALID_PRIORITIES:
        raise HTTPException(422, "Invalid priority filter")
    if (
        min_severity is not None
        and max_severity is not None
        and min_severity > max_severity
    ):
        raise HTTPException(422, "min_severity cannot exceed max_severity")

    try:
        items = get_sink().list_recent(
            limit,
            status=status,
            category=category,
            priority=priority,
            min_severity=min_severity,
            max_severity=max_severity,
        )
        return {"items": items, "count": len(items)}
    except Exception as exc:
        raise HTTPException(502, f"BigQuery query failed: {exc}") from exc


@router.get("/summary")
async def reports_summary(_officer: None = Depends(require_officer)):
    try:
        return get_sink().summary()
    except Exception as exc:
        raise HTTPException(502, f"BigQuery summary failed: {exc}") from exc


@router.patch("/{report_id}/status")
async def update_report_status(
    report_id: str,
    status: str,
    note: str | None = None,
    _officer: None = Depends(require_officer),
):
    if status not in VALID_STATUSES:
        raise HTTPException(422, "Invalid status")

    try:
        sink = get_sink()
        if not sink.get_report(report_id):
            raise HTTPException(404, "Report not found")
        updated = sink.update_status(report_id, status, note)
        return {"report_id": report_id, "status": status, "updated": updated}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Status update failed: {exc}") from exc


@router.get("/{report_id}/image")
async def get_report_image(
    report_id: str, _officer: None = Depends(require_officer)
):
    try:
        gcs_uri = get_sink().get_image_gcs_uri(report_id)
        if not gcs_uri:
            raise HTTPException(404, "No image found for this report")

        data, mime_type = get_evidence_storage().download_by_gcs_uri(gcs_uri)
        return Response(content=data, media_type=mime_type)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Image fetch failed: {exc}") from exc


@router.get("/{report_id}/status-history")
async def report_status_history(
    report_id: str, _officer: None = Depends(require_officer)
):
    try:
        sink = get_sink()
        if not sink.get_report(report_id):
            raise HTTPException(404, "Report not found")
        items = sink.status_history(report_id)
        return {"items": items, "count": len(items)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Status history query failed: {exc}") from exc


@router.get("/{report_id}")
async def report_detail(
    report_id: str, _officer: None = Depends(require_officer)
):
    try:
        report = get_sink().get_report(report_id)
        if not report:
            raise HTTPException(404, "Report not found")
        return report
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Report query failed: {exc}") from exc
