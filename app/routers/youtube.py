import os

from fastapi import APIRouter, HTTPException

from app.models.api import UploadYoutubeRequest
from app.services.google_auth import get_google_services
from app.services.youtube import upload_to_youtube

router = APIRouter(tags=["youtube"])

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")
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

    _, youtube = get_google_services()
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
def upload_batch(limit: int = 6):
    _, youtube = get_google_services()
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
