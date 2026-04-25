import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.settings import Settings
from app.database import get_transcription, get_highlights, set_highlights
from app.models.api import HighlightsResponse
from app.services.highlights_service import HighlightsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["highlights"])


def get_settings():
    return Settings()


@router.get("/highlights/{transcription_id}", response_model=HighlightsResponse)
def get_highlights_endpoint(transcription_id: int):
    row = get_transcription(transcription_id)
    if not row:
        raise HTTPException(status_code=404, detail="Transcription not found")
    highlights = get_highlights(transcription_id)
    if highlights is None:
        raise HTTPException(status_code=404, detail="Highlights not yet generated — POST /highlights/{id}")
    return HighlightsResponse(id=row["id"], file_path=row["file_path"], highlights=highlights)


@router.post("/highlights/{transcription_id}", response_model=HighlightsResponse)
def generate_highlights(
    transcription_id: int,
    n: int = Query(default=5, ge=1, le=20, description="Number of highlights to extract"),
    settings: Settings = Depends(get_settings),
):
    row = get_transcription(transcription_id)
    if not row:
        raise HTTPException(status_code=404, detail="Transcription not found")

    highlights = HighlightsService(settings).extract(dict(row), n=n)
    set_highlights(transcription_id, json.dumps(highlights, ensure_ascii=False))

    return HighlightsResponse(id=row["id"], file_path=row["file_path"], highlights=highlights)
