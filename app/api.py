import logging
import os

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.dependencies.auth import require_api_key

from app.database import init_db
from app.routers.auth import router as auth_router
from app.routers.audio import router as audio_router
from app.routers.documents import router as documents_router
from app.routers.highlights import router as highlights_router
from app.routers.flashcards import router as flashcards_router
from app.routers.groq import router as groq_router
from app.routers.ingestion import router as ingestion_router
from app.routers.openai import router as openai_router
from app.routers.search import router as search_router
from app.routers.summarize import router as summarize_router
from app.routers.transcriptions import router as transcriptions_router
from app.routers.youtube import router as youtube_router

load_dotenv()

app = FastAPI(title="Assistente Estudos API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_protected = [Depends(require_api_key)]

app.include_router(auth_router,          dependencies=_protected)
app.include_router(audio_router,         dependencies=_protected)
app.include_router(youtube_router,       dependencies=_protected)
app.include_router(ingestion_router,     dependencies=_protected)
app.include_router(search_router,        dependencies=_protected)
app.include_router(openai_router,        dependencies=_protected)
app.include_router(groq_router,          dependencies=_protected)
app.include_router(flashcards_router,    dependencies=_protected)
app.include_router(summarize_router,     prefix="/summarize", dependencies=_protected)
app.include_router(highlights_router,    dependencies=_protected)
app.include_router(transcriptions_router, prefix="/transcriptions", dependencies=_protected)
app.include_router(documents_router)


@app.on_event("startup")
def startup():
    init_db()
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if hf_token:
        try:
            from huggingface_hub import login
            login(hf_token)
        except ImportError:
            pass


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
