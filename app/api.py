import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from huggingface_hub import login

from app.database import init_db

from app.routers.audio import router as audio_router
from app.routers.frames import router as frames_router
from app.routers.flashcards import router as flashcards_router
from app.routers.groq import router as groq_router
from app.routers.ingestion import router as ingestion_router
from app.routers.openai import router as openai_router
from app.routers.search import router as search_router
from app.routers.summarize import router as summarize_router
from app.routers.sync import router as sync_router
from app.routers.youtube import router as youtube_router

load_dotenv()
login(os.getenv("HUGGINGFACE_TOKEN"))

app = FastAPI(title="Assistente Estudos API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sync_router)
app.include_router(audio_router)
app.include_router(frames_router)
app.include_router(youtube_router)
app.include_router(ingestion_router)
app.include_router(search_router)
app.include_router(openai_router)
app.include_router(groq_router)
app.include_router(flashcards_router)
app.include_router(summarize_router, prefix="/summarize")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
