import logging

from fastapi import APIRouter, Depends, HTTPException

from app.config.settings import Settings
from app.database import get_all_transcriptions, get_transcription, get_unsummarized, set_summary
from app.services.ingestion import _extract_class_meta
from app.models.api import SummarizeResponse
from app.services.summarizer import SummarizerService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["summarize"])


def get_settings():
    return Settings()


@router.get("", summary="List all transcriptions with summary status")
def list_transcriptions():
    rows = get_all_transcriptions()
    result = []
    for r in rows:
        meta = _extract_class_meta(r["file_path"])
        result.append({
            "id": r["id"],
            "file_path": r["file_path"],
            "video_url": r.get("video_url"),
            "status": r["status"],
            "summarized": r.get("summary") is not None,
            "summary": r.get("summary"),
            "created_at": r["created_at"],
            "course": meta["course"],
            "topic": meta["topic"],
            "aula_number": meta["aula_number"],
        })
    return result


@router.post("/{transcription_id}", response_model=SummarizeResponse)
def summarize_one(transcription_id: int, settings: Settings = Depends(get_settings)):
    row = get_transcription(transcription_id)
    if not row:
        raise HTTPException(status_code=404, detail="Transcription not found")

    summary, chunks = SummarizerService(settings).summarize(row["text"])
    set_summary(transcription_id, summary)

    return SummarizeResponse(
        id=row["id"],
        file_path=row["file_path"],
        summary=summary,
        chunks_processed=chunks,
    )


@router.post("/all", response_model=list[SummarizeResponse])
def summarize_all(settings: Settings = Depends(get_settings)):
    rows = get_unsummarized()
    if not rows:
        return []

    service = SummarizerService(settings)
    results = []

    for row in rows:
        try:
            summary, chunks = service.summarize(row["text"])
            set_summary(row["id"], summary)
            results.append(
                SummarizeResponse(
                    id=row["id"],
                    file_path=row["file_path"],
                    summary=summary,
                    chunks_processed=chunks,
                )
            )
        except Exception as exc:
            logger.error("Failed to summarize transcription %d: %s", row["id"], exc)

    return results
