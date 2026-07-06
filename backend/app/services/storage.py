from google.cloud import storage

from app.config import Settings

MIME_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class EvidenceStorage:
    def __init__(self, settings: Settings):
        self.enabled = settings.enable_image_storage
        self.bucket_name = settings.gcs_bucket_name
        self.client = storage.Client(project=settings.google_cloud_project) if self.enabled else None

    def upload_image(self, report_id: str, image_bytes: bytes | None, mime_type: str | None) -> str | None:
        if not self.enabled or self.client is None or not image_bytes or not mime_type:
            return None

        ext = MIME_EXT.get(mime_type)
        if not ext:
            raise RuntimeError(f"Unsupported image MIME type: {mime_type}")

        object_name = f"reports/{report_id}/evidence.{ext}"
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        return f"gs://{self.bucket_name}/{object_name}"
    def download_by_gcs_uri(self, gcs_uri: str) -> tuple[bytes, str]:
        if not self.client:
            raise RuntimeError("Storage client disabled")

        if not gcs_uri.startswith("gs://"):
            raise RuntimeError("Invalid GCS URI")

        path = gcs_uri.replace("gs://", "", 1)
        bucket_name, object_name = path.split("/", 1)

        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        data = blob.download_as_bytes()
        mime_type = blob.content_type or "application/octet-stream"

        return data, mime_type