from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    google_cloud_project: str = "citymind-ai-500910"
    google_cloud_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"
    bigquery_dataset: str = "citymind"
    bigquery_reports_table: str = "reports"
    enable_bigquery: bool = True
    max_image_bytes: int = 8 * 1024 * 1024
    cors_origins: str = "http://localhost:3000"
    officer_api_key: str = ""
    report_rate_limit_per_minute: int = 0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    enable_image_storage: bool = False
    gcs_bucket_name: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

@lru_cache
def get_settings() -> Settings:
    return Settings()
