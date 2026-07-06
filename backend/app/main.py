from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.reports import router as reports_router
from app.config import get_settings

app = FastAPI(title="CityMind AI API")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-CityMind-Officer-Key"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(reports_router, prefix="/api/v1/reports", tags=["reports"])
