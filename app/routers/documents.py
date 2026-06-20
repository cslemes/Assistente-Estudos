import platform
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.database import get_connection

router = APIRouter(tags=["documents"])


def _to_path(raw: str) -> Path:
    """Resolve a stored file path to a local Path.

    Paths in the DB may be absolute Windows paths (D:\\...) written by scripts
    on a different OS or host. We strip everything up to and including the
    'Downloads' segment and rejoin with the configured DOWNLOADS_BASE so that
    Docker and native environments both resolve correctly.
    """
    parts = raw.replace("\\", "/").split("/")
    try:
        idx = next(i for i, p in enumerate(parts) if p == "Downloads")
        rel = "/".join(parts[idx + 1:])
    except StopIteration:
        return Path(raw)  # no Downloads segment — use as-is
    from app.config.settings import Settings
    return Path(Settings().downloads_base) / rel

_SCAN_DIRS = {
    "documentos": "document",
    "scripts":    "notebook",
}

_MIME: dict[str, str] = {
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc":  "application/msword",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt":  "application/vnd.ms-powerpoint",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls":  "application/vnd.ms-excel",
    ".csv":  "text/csv",
    ".ipynb":"application/x-ipynb+json",
    ".py":   "text/x-python",
    ".md":   "text/markdown",
    ".txt":  "text/plain",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
}

MARKER_SUFFIX = ".storage"


def _storage_url(file_path: Path) -> str | None:
    """Return the public storage URL for an uploaded file, or None if not uploaded.

    The presence of a .storage marker means the file was uploaded. The URL is
    computed dynamically from the current STORAGE_PUBLIC_URL setting so that
    switching storage backends (MinIO → R2) doesn't leave stale localhost URLs.
    """
    marker = file_path.parent / (file_path.name + MARKER_SUFFIX)
    if not marker.exists():
        return None
    try:
        from app.services.storage import doc_key, public_url
        key = doc_key(str(file_path))
        url = public_url(key)
        return url or marker.read_text(encoding="utf-8").strip() or None
    except Exception:
        # Fallback to marker content if storage service is unavailable
        return marker.read_text(encoding="utf-8").strip() or None


def _lesson_dir(lesson_id: int) -> Path:
    """Resolve the lesson root folder from the DB audio file_path."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT file_path FROM transcriptions WHERE id = ?", (lesson_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    # file_path = .../ai_data/stem.mp3  →  parent.parent = lesson folder
    return _to_path(row["file_path"]).parent.parent


@router.get("/lessons/{lesson_id}/documents")
def list_documents(lesson_id: int) -> list[dict]:
    """List documents for a lesson. Each entry includes a `url` ready for download."""
    lesson = _lesson_dir(lesson_id)
    docs: list[dict] = []
    for subdir, category in _SCAN_DIRS.items():
        folder = lesson / subdir
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file() or f.suffix == MARKER_SUFFIX:
                continue
            ext = f.suffix.lower()
            storage = _storage_url(f)
            docs.append({
                "name":      f.name,
                "path":      f"{subdir}/{f.name}",
                "category":  category,
                "size":      f.stat().st_size,
                "mime_type": _MIME.get(ext, "application/octet-stream"),
                "extension": ext.lstrip("."),
                # url is either the public storage URL or the local download endpoint
                "url":       storage,
                "in_storage": storage is not None,
            })
    return docs


@router.get("/lessons/{lesson_id}/documents/download")
def download_document(lesson_id: int, file: str):
    """Download a document — redirects to storage if available, else serves locally."""
    lesson = _lesson_dir(lesson_id)
    target = (lesson / file).resolve()

    # Prevent path traversal outside the lesson folder
    if not str(target).startswith(str(lesson.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    storage = _storage_url(target)
    if storage:
        return RedirectResponse(url=storage, status_code=302)

    mime = _MIME.get(target.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{target.name}"'},
    )
