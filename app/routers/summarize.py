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

    # Group parts of the same lesson (same course + topic + aula_number) into one entry.
    # Google Meet often splits a single recording into multiple files (_1, _2, …).
    groups: dict[tuple, list] = {}
    for r in rows:
        meta = _extract_class_meta(r["file_path"])
        key = (meta["course"], meta["topic"], meta["aula_number"])
        groups.setdefault(key, []).append((meta["part_number"], r, meta))

    result = []
    for (course, topic, aula_number), parts in groups.items():
        # Sort by part_number so part 0 (main video) comes first
        parts.sort(key=lambda x: x[0])
        _, rep, meta = parts[0]

        # Use the first available video_url across all parts
        video_url = next((r.get("video_url") for _, r, _ in parts if r.get("video_url")), None)
        # Use the first available summary across all parts
        summary = next((r.get("summary") for _, r, _ in parts if r.get("summary")), None)

        result.append({
            "id": rep["id"],
            "file_path": rep["file_path"],
            "video_url": video_url,
            "status": rep["status"],
            "summarized": summary is not None,
            "summary": summary,
            "created_at": rep["created_at"],
            "course": course,
            "topic": topic,
            "aula_number": aula_number,
            "parts_count": len(parts),
        })

    return result


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


@router.post("/{transcription_id:int}", response_model=SummarizeResponse)
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
