# Academic Assistant (Jamworks Clone)

End-to-end academic intelligence system for capturing, processing, and retrieving knowledge from classes at the **AI Post-Graduation Program at PUC-Rio**.

## Feature Architecture

### 1. Transcripts & Search (RAG)

* **Engine:** Transcription via **Deepgram Nova-3** with speaker diarization.
* **Search:** Chunk storage in **Qdrant Cloud** with hybrid embeddings (dense + BM25 + ColBERT reranking).
* **Deep Link:** Each retrieved excerpt points to the exact second on YouTube (`?t=X`).

### 2. Highlights & Key Points

* **Intelligence:** Map-Reduce LLM pipeline over utterances to identify information density peaks.
* **Structure:** Automatic generation of titles, descriptions, and timestamps for key moments.
* **Navigation:** Clickable highlight cards in the web UI that seek the video to the exact moment.

### 3. Summary & Notes

* **Summary:** *Map-Reduce* technique to condense 3-hour classes into an executive study guide.
* **Format:** Markdown rendered inline in the web player.

### 4. Flashcards (Anki Integration)

* **Automation:** Atomic concept extraction → `.apkg` decks via `genanki`.
* **Active Study:** Support for Cloze Deletions and LaTeX formulas.

### 5. Visual Intelligence (Postponed)

CLIP + OCR pipeline for slide/notebook/whiteboard frame matching is designed but not yet implemented. The Qdrant payload schema already reserves `source_type`, `slide_thumb`, and related fields for when this ships.

---

## Cloud Stack

* **Compute:** Google Cloud Run (Python API) + RunPod Serverless (GPU workers for embed/NER/OCR).
* **Vector DB:** Qdrant Cloud (semantic memory).
* **Storage:** Cloudflare R2 (audio and slide images, zero egress cost).
* **Video:** YouTube API (unlisted video hosting).

---

## Data Schema (Qdrant Payload)

```json
{
  "text": "Chunk content...",
  "source_type": "transcript",
  "start_time": 348,
  "video_url": "https://youtu.be/ID?t=348",
  "topic": "Autoencoder",
  "course": "DL Python 25.1",
  "aula_number": 7,
  "entities": {}
}
```

---

## Project Structure

```text
app/
├── api.py                   # FastAPI entrypoint
├── database.py              # SQLite staging DB
├── config/settings.py       # Pydantic BaseSettings
├── models/
│   ├── api.py               # Request/Response schemas
│   └── embeddings.py        # SparseVector, QueryEmbeddings, Document
├── routers/
│   ├── search.py            # POST /search
│   ├── openai.py            # POST /ask, POST /ask/stream
│   ├── groq.py              # POST /ask/groq, POST /ask/groq/stream
│   ├── ingestion.py         # POST /ingest, GET /classes
│   ├── highlights.py        # GET/POST /highlights/{id}
│   ├── summarize.py         # GET /summarize, POST /summarize/{id}
│   ├── flashcards.py        # POST /flashcards
│   ├── audio.py             # POST /extract-audio, POST /transcribe
│   ├── sync.py              # POST /sync, POST /scrape
│   ├── transcriptions.py    # GET /transcriptions/{id}/segments
│   └── youtube.py           # POST /upload, POST /upload/batch
└── services/
    ├── sync.py              # Google Classroom → Drive download
    ├── drive.py             # Drive/Forms scraping + file org
    ├── transcription.py     # Deepgram Nova-3 PT-BR + diarization
    ├── youtube.py           # YouTube resumable upload
    ├── embedder.py          # Hybrid query embedder
    ├── retriever.py         # Qdrant 2-stage retrieval
    ├── openai_service.py    # OpenAI sync + streaming
    ├── groq_service.py      # Groq sync + streaming
    ├── llm_client.py        # Provider-agnostic chat client factory
    ├── ingestion.py         # Embed + NER + upload to Qdrant
    ├── summarizer.py        # Map-Reduce summarization
    ├── highlights_service.py# Map-Reduce highlights extraction
    ├── flashcard_service.py # Anki .apkg generation via genanki
    ├── runpod_client.py     # RunPod serverless GPU dispatch
    └── r2_storage.py        # Cloudflare R2 upload helpers
frontend/
├── src/
│   ├── pages/
│   │   ├── Home.tsx         # Course grid + global chat
│   │   └── Player.tsx       # 3-column lesson player
│   ├── components/
│   │   ├── VideoPlayer.tsx
│   │   ├── TranscriptTab.tsx
│   │   ├── HighlightsTab.tsx
│   │   ├── FlashcardsTab.tsx
│   │   ├── AiChat.tsx
│   │   ├── CourseSidebar.tsx
│   │   └── TopBar.tsx
│   ├── api.ts               # Typed fetch helpers + SSE stream
│   └── types.ts             # Shared TypeScript interfaces
runpod_workers/              # Local mock GPU worker (Docker)
scripts/
├── rename_videos.py         # Rename videos to Aula_NN_Topic.mp4
├── transcribe_folder.py     # Batch transcription trigger
├── sync_video_urls.py       # Backfill YouTube URLs in SQLite
├── video_cutter.py          # Local video trimming utility
└── cleanup.py               # Reset ai_data/ and DB records
streamlit_app.py             # Legacy CLI chat UI
main.py                      # CLI trigger
```

---

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Python 3.13+
- Node.js 20+ (for the frontend)
- A `.env` file with the required credentials (see below)

### Install dependencies

```bash
uv sync                      # Python backend
cd frontend && npm install   # React frontend
```

### Environment variables

Copy `.env.template` to `.env` and fill in the values:

```bash
cp .env.template .env
```

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `GROQ_API_KEY` | Groq API key |
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `DEEPGRAM_API_KEY` | Deepgram API key |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `YOUTUBE_CHANNEL_ID` | Target YouTube channel |
| `USE_RUNPOD` | `true` to route embed/NER to RunPod workers |
| `RUNPOD_API_KEY` | RunPod API key (if `USE_RUNPOD=true`) |
| `RUNPOD_EMBED_ENDPOINT_ID` | RunPod endpoint for embeddings |
| `RUNPOD_NER_ENDPOINT_ID` | RunPod endpoint for NER |

---

## Google Cloud Platform (GCP) Setup

The sync pipeline requires a GCP OAuth 2.0 desktop client with three APIs enabled.

### 1. Create a GCP Project

Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project (e.g. `Academic-Assistant`).

### 2. Enable the required APIs

In **APIs & Services → Library**, enable:

| API | Used for |
|-----|----------|
| **Google Classroom API** | List courses, topics, assignments and materials |
| **Google Drive API** | Download attached files and traverse shared folders |
| **YouTube Data API v3** | Upload class recordings as unlisted videos |

### 3. Configure the OAuth consent screen

Go to **APIs & Services → OAuth consent screen** and add these scopes:

```
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly
https://www.googleapis.com/auth/classroom.coursework.me.readonly
https://www.googleapis.com/auth/classroom.announcements.readonly
https://www.googleapis.com/auth/classroom.topics.readonly
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/youtube.upload
```

Add your Google account as a **test user**.

### 4. Create OAuth credentials

Go to **Credentials → Create Credentials → OAuth client ID → Desktop app**, download the JSON, and save it as `credentials.json` in the project root.

### 5. First-time authentication

On the first `POST /sync`, the app opens a browser to grant permissions. A `token.json` is saved and reused on subsequent runs. Both files are in `.gitignore`.

---

## Running Locally

### API server

```bash
uv run uvicorn app.api:app --reload
```

Available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### Frontend (dev)

```bash
cd frontend && npm run dev
```

Available at `http://localhost:3000`.

### Full stack (Docker Compose)

Spins up the API, the React frontend, and the local RunPod GPU worker mock:

```bash
docker compose up
```

---

## REST API Endpoints

```text
GET  /health
POST /sync                         # Download from Classroom
POST /scrape                       # Download from Drive/Forms URL
POST /transcribe                   # Deepgram transcription
POST /extract-audio                # FFmpeg audio extraction (single)
POST /extract-audio/batch          # FFmpeg audio extraction (batch)
POST /upload                       # Upload single video to YouTube
POST /upload/batch?limit=6         # Batch upload (default 6/day)
POST /ingest                       # Embed + NER + send to Qdrant
GET  /classes                      # List distinct classes in Qdrant
GET  /transcriptions/pending       # List pending for embedding
GET  /transcriptions/{id}/segments # Utterance segments for a lesson
PATCH /transcriptions/{id}/status  # Update transcription status
POST /search                       # Hybrid vector search
POST /ask                          # RAG answer (sync, OpenAI)
POST /ask/stream                   # RAG answer (SSE streaming, OpenAI)
POST /ask/groq                     # RAG answer (sync, Groq)
POST /ask/groq/stream              # RAG answer (SSE streaming, Groq)
GET  /highlights/{id}              # Fetch stored highlights
POST /highlights/{id}              # Generate highlights via Map-Reduce LLM
GET  /summarize                    # List transcriptions with summary status
POST /summarize/{id}               # Map-Reduce summarize one transcription
POST /summarize/all                # Map-Reduce summarize all pending
POST /flashcards                   # Generate Anki .apkg deck
```

---

## Pipeline Flow

```text
POST /sync              → Download files from Google Classroom
POST /extract-audio     → FFmpeg: video → .mp3
POST /transcribe        → Deepgram → .txt + .json (utterances) + SQLite (status=pending)
POST /ingest            → NER + embed transcripts → Qdrant (status=sent)
POST /upload            → Upload video to YouTube, store URL in SQLite
POST /highlights/{id}   → Map-Reduce → highlights stored in SQLite
POST /summarize/{id}    → Map-Reduce → summary stored in SQLite
POST /flashcards        → Qdrant chunks → LLM → Anki .apkg
POST /ask/groq/stream   → Query → hybrid search → streaming LLM answer
```

---

## Implementation Status

| Feature | Status |
|---------|--------|
| Transcripts & Search (RAG) | Implemented |
| SQLite staging DB (pending → embedded → sent) | Implemented |
| NER enrichment (`lfcc/bert-portuguese-ner`) | Implemented |
| Utterance-level chunking with timestamps | Implemented |
| Qdrant Cloud — ingestion + retrieval | Implemented |
| Hybrid search (dense + BM25 + ColBERT rerank) | Implemented |
| Streaming RAG (SSE) | Implemented |
| Google Classroom sync | Implemented |
| Deepgram Nova-3 PT-BR diarization | Implemented |
| YouTube resumable upload (auto token refresh) | Implemented |
| Groq LLM sync + streaming | Implemented |
| FFmpeg audio extraction | Implemented |
| Summary / Map-Reduce | Implemented |
| Highlights / Key Points | Implemented |
| Flashcards (Anki/genanki) | Implemented |
| React web player (transcript, highlights, flashcards, resumo tabs) | Implemented |
| RunPod GPU worker dispatch (embed + NER) | Implemented |
| Visual Intelligence (CLIP + OCR frame pipeline) | Postponed |
| Discord Bot | Not started |

---

## External Services

| Service | Purpose | Status |
|---------|---------|--------|
| Deepgram Nova-3 | Speech-to-text (PT-BR) + diarization | Implemented |
| Google Classroom API | Courses, topics, assignments | Implemented |
| Google Drive API | File download/listing | Implemented |
| YouTube Data API | Unlisted video upload | Implemented |
| Playwright/Chromium | Google Forms scraping | Implemented |
| FFmpeg | Audio extraction | Implemented |
| Qdrant Cloud | Vector DB for RAG search | Implemented |
| OpenAI GPT-4o-mini | RAG answer generation | Implemented |
| Groq (llama-3.3-70b) | RAG answer generation (fast) | Implemented |
| Anki/genanki | Flashcard .apkg generation | Implemented |
| RunPod Serverless | GPU workers for embed + NER | Implemented |
| Cloudflare R2 | Asset storage | Configured |
| LangSmith | LLM tracing (optional) | Configured |
| LibreOffice / EasyOCR / CLIP | Visual intelligence pipeline | Postponed |
