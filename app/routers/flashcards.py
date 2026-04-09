import logging
import os
from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.config.settings import Settings
from app.models.api import FlashcardRequest
from app.services.flashcard_service import FlashcardService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_flashcard_service() -> FlashcardService:
    return FlashcardService(settings=get_settings())


@router.post("")
async def generate_flashcards(
    request: FlashcardRequest,
    background_tasks: BackgroundTasks,
    service: FlashcardService = Depends(get_flashcard_service),
):
    try:
        apkg_path = service.generate_apkg(
            topic=request.topic,
            course=request.course,
            aula_number=request.aula_number,
            num_cards=request.num_cards,
            deck_name=request.deck_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error("Flashcard generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")

    parts = [p for p in [request.course, request.topic] if p]
    label = "_".join(parts) if parts else "pucrio_ia"
    filename = f"flashcards_{label}.apkg".replace(" ", "_")

    background_tasks.add_task(os.unlink, apkg_path)

    return FileResponse(
        path=apkg_path,
        media_type="application/octet-stream",
        filename=filename,
    )
