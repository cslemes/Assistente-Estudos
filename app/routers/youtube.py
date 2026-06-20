import os

from fastapi import APIRouter, HTTPException

from app.config.settings import VIDEO_EXTENSIONS
from app.database import set_video_url_by_stem
from app.models.api import UploadStorageRequest, UploadYoutubeRequest
from app.services.google_auth import get_google_services
from app.services.youtube import upload_to_youtube
import app.services.storage as storage_svc

router = APIRouter(tags=["youtube"])
DOWNLOADS_DIR = os.path.join(os.getcwd(), "Downloads")


def _find_pending_videos(root: str) -> list[str]:
    pending = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.lower().endswith(VIDEO_EXTENSIONS):
                full_path = os.path.join(dirpath, fname)
                if not os.path.exists(full_path + ".uploaded"):
                    pending.append(full_path)
    return pending


@router.post("/upload")
def upload_youtube_job(payload: UploadYoutubeRequest):
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    _, _, youtube = get_google_services()
    upload_to_youtube(youtube, payload.file_path, payload.title, payload.description)

    marker_file = payload.file_path + ".uploaded"
    video_id = None
    if os.path.exists(marker_file):
        with open(marker_file, "r", encoding="utf-8") as f:
            video_id = f.read().strip()

    return {
        "file_path": payload.file_path,
        "uploaded": os.path.exists(marker_file),
        "video_id": video_id,
    }


@router.post("/upload/batch")
def upload_batch(limit: int = 15):
    _, _, youtube = get_google_services()
    pending = _find_pending_videos(DOWNLOADS_DIR)[:limit]

    results = []
    for file_path in pending:
        title = os.path.splitext(os.path.basename(file_path))[0]
        upload_to_youtube(youtube, file_path, title, "")
        marker_file = file_path + ".uploaded"
        video_id = None
        if os.path.exists(marker_file):
            with open(marker_file, "r", encoding="utf-8") as f:
                video_id = f.read().strip()
        results.append({"file_path": file_path, "video_id": video_id})

    return {"uploaded": len(results), "files": results}


# ---------------------------------------------------------------------------
# S3-compatible object storage (MinIO / R2 / S3)
# ---------------------------------------------------------------------------

@router.post("/upload/storage")
def upload_storage(payload: UploadStorageRequest):
    """Upload a video to the configured S3-compatible storage and update the DB video_url."""
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    if not storage_svc.is_configured():
        raise HTTPException(status_code=503, detail="Object storage not configured (check STORAGE_* env vars)")

    key = payload.object_key or storage_svc.video_key(payload.file_path)
    url = storage_svc.upload_file(payload.file_path, key)

    if not url:
        raise HTTPException(status_code=500, detail="Upload failed — check storage credentials and bucket")

    stem = os.path.splitext(os.path.basename(payload.file_path))[0]
    updated = set_video_url_by_stem(stem, url)

    return {"file_path": payload.file_path, "object_key": key, "video_url": url, "db_rows_updated": updated}


@router.post("/upload/storage/batch")
def upload_storage_batch(limit: int = 0):
    """Upload all pending videos (no .storage marker) to object storage."""
    if not storage_svc.is_configured():
        raise HTTPException(status_code=503, detail="Object storage not configured (check STORAGE_* env vars)")

    pending = _find_pending_videos(DOWNLOADS_DIR)
    # filter already uploaded to storage
    pending = [p for p in pending if not os.path.exists(p + ".storage")]
    if limit:
        pending = pending[:limit]

    results = []
    for file_path in pending:
        key = storage_svc.video_key(file_path)
        url = storage_svc.upload_file(file_path, key)
        if url:
            open(file_path + ".storage", "w").close()
            stem = os.path.splitext(os.path.basename(file_path))[0]
            set_video_url_by_stem(stem, url)
        results.append({"file_path": file_path, "video_url": url, "ok": url is not None})

    ok = sum(1 for r in results if r["ok"])
    return {"total": len(results), "uploaded": ok, "files": results}
