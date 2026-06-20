from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.api import ScrapeDownloadRequest
from app.services.drive import download_with_prefix, get_drive_links_from_form
from app.services.google_auth import get_google_services
from app.services.sync import run_sync

router = APIRouter(tags=["sync"])

_status_lock = Lock()
_sync_status = {
    "running": False,
    "last_started_at": None,
    "last_finished_at": None,
    "last_result": None,
    "last_error": None,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_running(running: bool):
    with _status_lock:
        _sync_status["running"] = running
        if running:
            _sync_status["last_started_at"] = _utc_now_iso()
            _sync_status["last_error"] = None
        else:
            _sync_status["last_finished_at"] = _utc_now_iso()


def _run_sync_job():
    _set_running(True)
    try:
        result = run_sync()
        with _status_lock:
            _sync_status["last_result"] = result
    except Exception as exc:
        with _status_lock:
            _sync_status["last_error"] = str(exc)
    finally:
        _set_running(False)


@router.get("/status")
def status():
    with _status_lock:
        return dict(_sync_status)


@router.post("/sync")
def sync(background_tasks: BackgroundTasks, background: bool = True):
    with _status_lock:
        if _sync_status["running"]:
            raise HTTPException(status_code=409, detail="Sync is already running")

    if background:
        background_tasks.add_task(_run_sync_job)
        return {"message": "Sync started in background"}

    _run_sync_job()
    with _status_lock:
        return {
            "message": "Sync finished",
            "result": _sync_status["last_result"],
            "error": _sync_status["last_error"],
        }


@router.post("/scrape")
def scrape_download_job(payload: ScrapeDownloadRequest):
    ids = get_drive_links_from_form(payload.url)
    _, drive, _ = get_google_services()

    downloaded_files = []
    for drive_id in ids:
        downloaded_files.extend(
            download_with_prefix(drive, drive_id, payload.topic_path, payload.prefix)
        )

    return {
        "url": payload.url,
        "ids_found": len(ids),
        "files_downloaded": len(downloaded_files),
        "downloaded_files": downloaded_files,
    }
