import logging
import os
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_r2_client():
    import boto3
    from app.config.settings import Settings
    s = Settings()
    if not all([s.cloudflare_account_id, s.cloudflare_r2_access_key_id, s.cloudflare_r2_secret_access_key]):
        return None
    return boto3.client(
        "s3",
        endpoint_url=f"https://{s.cloudflare_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=s.cloudflare_r2_access_key_id,
        aws_secret_access_key=s.cloudflare_r2_secret_access_key,
        region_name="auto",
    )


def upload_thumbnail(local_path: str, object_key: str) -> str | None:
    """Upload a file to R2 and return its public URL, or None if R2 is not configured."""
    from app.config.settings import Settings
    s = Settings()

    if not s.cloudflare_r2_public_url or not s.cloudflare_r2_bucket_name:
        return None

    client = _get_r2_client()
    if client is None:
        return None

    try:
        client.upload_file(
            local_path,
            s.cloudflare_r2_bucket_name,
            object_key,
            ExtraArgs={"ContentType": "image/png"},
        )
        public_url = s.cloudflare_r2_public_url.rstrip("/")
        return f"{public_url}/{object_key}"
    except Exception as exc:
        logger.warning("R2 upload failed for %s: %s", object_key, exc)
        return None


def thumbnail_key(video_path: str, slide_index: int) -> str:
    """Build a deterministic R2 object key for a slide thumbnail."""
    p = Path(video_path)
    course = p.parent.parent.parent.name
    topic = p.parent.parent.name
    stem = p.stem
    return f"thumbnails/{course}/{topic}/{stem}/slide_{slide_index:04d}.png"
