"""
Generic S3-compatible object storage client.

Works with MinIO (local), Cloudflare R2, AWS S3, or any S3-compatible service.
Configure via environment variables:

  STORAGE_ENDPOINT_URL=http://localhost:9000   # MinIO; omit for real AWS S3
  STORAGE_ACCESS_KEY_ID=minioadmin
  STORAGE_SECRET_ACCESS_KEY=minioadmin
  STORAGE_BUCKET_NAME=videos
  STORAGE_PUBLIC_URL=http://localhost:9000/videos  # public base URL for video links
"""

import logging
import mimetypes
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_client(endpoint_url: str, access_key: str, secret_key: str, region: str):
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )


def _client_from_settings():
    from app.config.settings import Settings
    s = Settings()
    if not s.storage_access_key_id or not s.storage_secret_access_key:
        return None, s
    client = _get_client(
        s.storage_endpoint_url or "",
        s.storage_access_key_id,
        s.storage_secret_access_key,
        s.storage_region,
    )
    return client, s


def upload_file(local_path: str, object_key: str, content_type: str | None = None) -> str | None:
    """Upload a file and return its public URL, or None if storage is not configured."""
    client, s = _client_from_settings()
    if client is None:
        logger.warning("Object storage not configured — skipping upload of %s", local_path)
        return None

    if content_type is None:
        content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"

    try:
        client.upload_file(
            local_path,
            s.storage_bucket_name,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )
        return public_url(object_key)
    except Exception as exc:
        logger.error("Storage upload failed for %s: %s", local_path, exc)
        return None


def public_url(object_key: str) -> str | None:
    """Build the public URL for an object key."""
    from app.config.settings import Settings
    s = Settings()
    if not s.storage_public_url:
        return None
    return f"{s.storage_public_url.rstrip('/')}/{object_key}"


def video_key(video_path: str) -> str:
    """Deterministic object key for a video file: course/topic/filename.mp4"""
    p = Path(video_path)
    course = p.parent.parent.parent.name
    topic = p.parent.parent.name
    return f"{course}/{topic}/{p.name}"


def doc_key(doc_path: str) -> str:
    """Deterministic object key for a document: course/topic/subdir/filename
    e.g. Downloads/Course/Aula_01/documentos/file.pdf → Course/Aula_01/documentos/file.pdf
    """
    p = Path(doc_path)
    course = p.parent.parent.parent.name
    topic  = p.parent.parent.name
    subdir = p.parent.name          # "documentos" or "scripts"
    return f"{course}/{topic}/{subdir}/{p.name}"


def is_configured() -> bool:
    from app.config.settings import Settings
    s = Settings()
    return bool(s.storage_access_key_id and s.storage_secret_access_key)
