import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_transcription

router = APIRouter(tags=["transcriptions"])


class SegmentOut(BaseModel):
    text: str
    start: float
    end: float
    speaker: int | None


@router.get("/{transcription_id}/segments", response_model=list[SegmentOut], summary="Get transcript segments for a transcription")
def get_segments(transcription_id: int):
    """Return parsed utterance segments for the given transcription ID."""
    row = get_transcription(transcription_id)
    if not row:
        raise HTTPException(status_code=404, detail="Transcription not found")

    segments_json = row.get("segments_json")
    if not segments_json:
        raise HTTPException(status_code=404, detail="Segments not available")

    segments = json.loads(segments_json)
    if not segments:
        raise HTTPException(status_code=404, detail="Segments stored but empty")

    return segments
