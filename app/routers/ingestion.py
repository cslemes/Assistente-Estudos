from fastapi import APIRouter, HTTPException

from app.config.settings import Settings
from app.database import get_pending, set_status
from app.services.ingestion import ingest_pending_transcriptions

router = APIRouter(tags=["ingestion"])


@router.get("/classes")
def list_classes():
    from qdrant_client import QdrantClient
    settings = Settings()
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    seen = set()
    classes = []
    offset = None

    while True:
        results, next_offset = client.scroll(
            collection_name=settings.collection_name,
            with_payload=["course", "topic", "aula_number"],
            with_vectors=False,
            limit=1000,
            offset=offset,
        )
        for point in results:
            p = point.payload or {}
            key = (p.get("course"), p.get("topic"), p.get("aula_number"))
            if key not in seen:
                seen.add(key)
                classes.append({
                    "course": p.get("course"),
                    "topic": p.get("topic"),
                    "aula_number": p.get("aula_number"),
                })
        if next_offset is None:
            break
        offset = next_offset

    classes.sort(key=lambda c: (c["course"] or "", c["aula_number"] or 0))
    return {"count": len(classes), "classes": classes}


@router.post("/ingest")
def ingest(collection: str = None):
    return ingest_pending_transcriptions(collection)


@router.get("/transcriptions/pending")
def transcriptions_pending():
    rows = get_pending()
    return {"count": len(rows), "transcriptions": rows}


@router.patch("/transcriptions/{transcription_id}/status")
def update_transcription_status(transcription_id: int, status: str):
    if status not in ("pending", "embedded", "sent"):
        raise HTTPException(status_code=400, detail="status must be pending, embedded, or sent")
    set_status(transcription_id, status)
    return {"id": transcription_id, "status": status}
