import logging
from fastapi import APIRouter, Depends, HTTPException
from app.config.settings import Settings
from app.database import get_transcription
from app.services.ingestion import _extract_class_meta
from app.services.retriever import QdrantRetriever

logger = logging.getLogger(__name__)
router = APIRouter(tags=["visual"])


def get_settings():
    return Settings()


def get_retriever(settings: Settings = Depends(get_settings)):
    return QdrantRetriever(settings=settings)


@router.get("/visual/{lesson_id}")
def get_visual_chunks(
    lesson_id: int,
    retriever: QdrantRetriever = Depends(get_retriever),
):
    row = get_transcription(lesson_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")

    meta = _extract_class_meta(row["file_path"])
    return retriever.scroll_visual(
        course=meta["course"],
        topic=meta["topic"],
        aula_number=meta["aula_number"],
    )
