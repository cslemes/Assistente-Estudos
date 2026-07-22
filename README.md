# Assistente de Estudos

End-to-end academic intelligence system for capturing, processing, and retrieving knowledge from classes at the **AI Post-Graduation Program at PUC-Rio**.

## Features

### 1. Transcripts & Search (RAG)
- Transcription via **Deepgram Nova-3** with speaker diarization (PT-BR)
- Chunk storage in **Qdrant Cloud** with hybrid embeddings (dense + BM25 + ColBERT reranking)
- Each retrieved excerpt deep-links to the exact second in the video

### 2. Highlights & Key Points
- Map-Reduce LLM pipeline over utterances to identify information density peaks
- Clickable highlight cards in the web player seek the video to the exact timestamp

### 3. Summary & Notes
- Map-Reduce condensation of 3-hour classes into an executive study guide
- Rendered as Markdown inline in the web player

### 4. Flashcards (Anki Integration)
- Atomic concept extraction → `.apkg` decks via `genanki`
- Supports Cloze Deletions and LaTeX formulas

### 5. Documents Tab
- Lists course documents (PDFs, slides, notebooks) stored in S3-compatible storage
- Download URLs served from the current `STORAGE_PUBLIC_URL` setting (MinIO locally, R2 in production)

### 6. Visual Intelligence *(Postponed)*
- CLIP + OCR pipeline for slide/notebook/whiteboard frame matching is designed but not yet implemented
- Qdrant payload schema already reserves `source_type`, `slide_thumb`, and related fields

---

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Python 3.13 on **Google Cloud Run** |
| Frontend | React + Vite + Ant Design, served via **nginx** |
| Auth | **Firebase Authentication** (Google Sign-In) |
| Vector DB | **Qdrant Cloud** |
| Storage | **Cloudflare R2** (production) / **MinIO** (local) |
| Video | **YouTube API** (unlisted hosting) |
| GPU Workers | **RunPod Serverless** (embed + NER) |
| Transcription | **Deepgram Nova-3** |
| LLM | **Groq** (llama) / **OpenAI** (GPT-4o-mini) |
| CI/CD | **GitHub Actions** → **GitHub Container Registry** |

---

## Project Structure

```text
app/
├── api.py                   # FastAPI entrypoint
├── database.py              # SQLite staging DB
├── config/settings.py       # Pydantic BaseSettings
├── models/api.py            # Request/Response schemas
├── routers/
│   ├── auth.py              # Google OAuth (Classroom/Drive/YouTube)
│   ├── sync.py              # POST /sync, POST /scrape
│   ├── youtube.py           # POST /upload, POST /upload/batch
│   ├── openai.py            # POST /ask, POST /ask/stream
│   ├── groq.py              # POST /ask/groq, POST /ask/groq/stream
│   └── documents.py         # GET /lessons/{id}/documents
└── services/
    ├── sync.py              # Google Classroom → Drive download
    ├── drive.py             # Drive/Forms scraping + file org
    ├── transcription.py     # Deepgram Nova-3 PT-BR + diarization
    ├── youtube.py           # YouTube resumable upload
    ├── embedder.py          # Hybrid query embedder
    ├── retriever.py         # Qdrant 2-stage retrieval
    ├── ingestion.py         # Embed + NER + upload to Qdrant
    ├── summarizer.py        # Map-Reduce summarization
    ├── flashcard_service.py # Anki .apkg generation via genanki
    ├── storage.py           # S3-compatible storage (MinIO / R2)
    ├── google_auth.py       # OAuth token management
    └── runpod_client.py     # RunPod serverless GPU dispatch
frontend/
├── src/
│   ├── firebase.ts          # Firebase app init + Google provider
│   ├── hooks/useAuth.ts     # onAuthStateChanged hook
│   ├── pages/
│   │   ├── Login.tsx        # Google Sign-In screen
│   │   ├── Home.tsx         # Course grid + global chat
│   │   └── Player.tsx       # 3-column lesson player
│   └── components/
│       ├── AuthGuard.tsx    # Route protector → /login if unauthenticated
│       ├── TopBar.tsx       # Breadcrumb + progress + logout button
│       ├── VideoPlayer.tsx
│       ├── TranscriptTab.tsx
│       ├── HighlightsTab.tsx
│       ├── FlashcardsTab.tsx
│       ├── DocsTab.tsx      # Documents tab
│       ├── AiChat.tsx
│       └── CourseSidebar.tsx
├── Dockerfile               # Multi-stage build (node → nginx)
└── nginx.conf               # SPA fallback + API proxy
runpod_workers/
├── embed/                   # Hybrid embedding worker (dense + BM25 + ColBERT)
└── ner/                     # Portuguese NER worker (bert-portuguese-ner)
scripts/
├── organize_downloads.py    # Folder rename + video file clean + SQLite/Qdrant sync
├── transcribe_folder.py     # Batch transcription trigger
├── upload_docs.py           # Upload documents to S3 storage
├── upload_videos.py         # Upload videos to S3 storage
├── video_cutter.py          # Silero VAD silence trimming
└── reset_collection.py      # Drop and recreate Qdrant collection
.github/workflows/
└── docker-publish.yml       # Build + push API and frontend images to GHCR
```

---

## Quick Start (Docker)

### Local development

```bash
cp .env.template .env   # fill in credentials
docker compose up
```

- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001` (minioadmin / minioadmin)

### Production (pull from GHCR)

```bash
cp .env.template .env   # fill in production credentials
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## Environment Variables

Copy `.env.template` to `.env` and fill in values:

| Variable | Description |
|----------|-------------|
| `DEEPGRAM_API_KEY` | Deepgram API key |
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `GROQ_API_KEY` | Groq API key |
| `GROQ_MODEL` | Groq model name |
| `OPENAI_API_KEY` | OpenAI API key |
| `LLM_PROVIDER` | `groq` (default) or `openai` |
| `TRANSCRIPTION_PROVIDER` | `deepgram` (default), `openai`, or `groq` |
| `STORAGE_ENDPOINT_URL` | S3 endpoint (`http://localhost:9000` for MinIO) |
| `STORAGE_ACCESS_KEY_ID` | S3 access key |
| `STORAGE_SECRET_ACCESS_KEY` | S3 secret key |
| `STORAGE_BUCKET_NAME` | S3 bucket name |
| `STORAGE_PUBLIC_URL` | Public base URL for stored files |
| `DOWNLOADS_BASE` | Path to Downloads folder (`/app/Downloads` in Docker) |
| `BACKEND_API_KEY` | Shared API key required on all non-health routes (leave empty to disable) |
| `VITE_BACKEND_API_KEY` | Same value as `BACKEND_API_KEY` — baked into frontend bundle |
| `USE_RUNPOD` | `true` to route embed/NER to RunPod GPU workers |
| `RUNPOD_API_KEY` | RunPod API key |
| `RUNPOD_EMBED_ENDPOINT_ID` | RunPod embed endpoint |
| `RUNPOD_NER_ENDPOINT_ID` | RunPod NER endpoint |
| `VITE_FIREBASE_*` | Firebase web app config (6 values — see `.env.template`) |

---

## Firebase Authentication Setup

1. Create a project at [console.firebase.google.com](https://console.firebase.google.com)
2. Add a **Web app** and copy the config values into `.env` as `VITE_FIREBASE_*`
3. Go to **Authentication → Sign-in method** → enable **Google**
4. Go to **Authentication → Settings → Authorized domains** → add your domain (and `localhost` for local dev)

Firebase vars are baked into the frontend bundle at build time via Docker build args. The GitHub Actions workflow reads them from repository secrets.

---

## Google Cloud Platform Setup

Required for Classroom sync, Drive download, and YouTube upload.

### 1. Enable APIs

In [GCP Console](https://console.cloud.google.com) → **APIs & Services → Library**, enable:

| API | Purpose |
|-----|---------|
| Google Classroom API | List courses, topics, assignments |
| Google Drive API | Download attached files |
| YouTube Data API v3 | Upload recordings as unlisted videos |

### 2. OAuth Consent Screen scopes

```
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly
https://www.googleapis.com/auth/classroom.coursework.me.readonly
https://www.googleapis.com/auth/classroom.announcements.readonly
https://www.googleapis.com/auth/classroom.topics.readonly
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/youtube.upload
```

### 3. Create credentials

**Credentials → Create Credentials → OAuth client ID → Desktop app** → download JSON → save as `credentials.json` in project root. On first `POST /sync` the app opens a browser to grant permissions; `token.json` is saved and reused. Both files are in `.gitignore`.

---

## CI/CD

GitHub Actions builds both images on every push to `main` and pushes to GHCR:

```
ghcr.io/cslemes/assistente-api:latest
ghcr.io/cslemes/assistente-frontend:latest
```

Add these secrets to the **production** environment in **Settings → Environments → production → Secrets**:

```
VITE_FIREBASE_API_KEY
VITE_FIREBASE_AUTH_DOMAIN
VITE_FIREBASE_PROJECT_ID
VITE_FIREBASE_STORAGE_BUCKET
VITE_FIREBASE_MESSAGING_SENDER_ID
VITE_FIREBASE_APP_ID
VITE_BACKEND_API_KEY
```

---

## Security

### API Authentication

All routes except `GET /health` require an `X-Api-Key` header matching `BACKEND_API_KEY`. When the env var is empty the check is skipped (safe for local dev).

Generate a key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set the same value for both `BACKEND_API_KEY` (API) and `VITE_BACKEND_API_KEY` (frontend build arg) in `.env`.

### Network Isolation

The API container has **no exposed ports** — it is only reachable through the nginx frontend container on port 3000. All external traffic goes through nginx, which proxies `/api/*` to the API internally.

### Security Fixes Applied

| ID | Severity | Description | Fix |
|----|----------|-------------|-----|
| vuln-0001 | HIGH (CVSS 7.5) | Path traversal in document download — string prefix check bypassable via sibling directory names | `Path.is_relative_to()` filesystem-aware containment |
| vuln-0002 | HIGH (CVSS 8.6) | No server-side auth on any route — unauthenticated callers could invoke all API operations | `X-Api-Key` dependency on all routers + API port removed from compose |
| vuln-0003 | HIGH (CVSS 8.6) | SSRF in `/scrape` — user-supplied URL passed directly to Playwright | Allowlist restricted to Google domains (`docs.google.com`, `drive.google.com`, `forms.gle`) |

---

## API Endpoints

```text
GET  /health
POST /sync                         # Download from Google Classroom
POST /scrape                       # Download from Drive/Forms URL
POST /extract-audio                # FFmpeg audio extraction
POST /extract-audio/batch
POST /transcribe                   # Deepgram transcription
POST /ingest                       # Embed + NER → Qdrant
GET  /transcriptions/pending
PATCH /transcriptions/{id}/status
POST /upload                       # Upload video to YouTube
POST /upload/batch
POST /upload/storage               # Upload to S3 storage
POST /upload/storage/batch
GET  /lessons/{id}/documents       # List documents for a lesson
POST /search                       # Hybrid vector search
POST /ask                          # RAG answer (OpenAI, sync)
POST /ask/stream                   # RAG answer (OpenAI, SSE)
POST /ask/groq                     # RAG answer (Groq, sync)
POST /ask/groq/stream              # RAG answer (Groq, SSE)
GET  /summarize
POST /summarize/{id}               # Map-Reduce summarize
POST /summarize/all
POST /flashcards/generate          # Generate Anki .apkg
```

---

## Pipeline Flow

```text
POST /sync              → Download files from Google Classroom
POST /extract-audio     → FFmpeg: video → audio
POST /transcribe        → Deepgram → transcript + SQLite (status=pending)
POST /ingest            → NER + embed → Qdrant (status=sent)
POST /upload            → Video → YouTube, URL stored in SQLite
POST /summarize/{id}    → Map-Reduce → summary in SQLite
POST /ask/groq/stream   → Query → hybrid search → streaming answer
POST /flashcards/generate → Qdrant chunks → LLM → Anki .apkg
```

---

## Implementation Status

| Feature | Status |
|---------|--------|
| Transcripts & Search (RAG) | ✅ Done |
| Hybrid search (dense + BM25 + ColBERT) | ✅ Done |
| Streaming RAG (SSE) | ✅ Done |
| Google Classroom / Drive sync | ✅ Done |
| Deepgram Nova-3 PT-BR diarization | ✅ Done |
| YouTube upload (auto token refresh) | ✅ Done |
| Groq + OpenAI LLM support | ✅ Done |
| Summary / Map-Reduce | ✅ Done |
| Highlights / Key Points | ✅ Done |
| Flashcards (Anki/genanki) | ✅ Done |
| Documents tab (S3 storage) | ✅ Done |
| Firebase Google Authentication | ✅ Done |
| Per-user watch progress (Firestore) | ✅ Done |
| Backend API key auth (X-Api-Key) | ✅ Done |
| Security fixes (path traversal, SSRF, missing auth) | ✅ Done |
| React web player | ✅ Done |
| Docker Compose (local + prod) | ✅ Done |
| GitHub Actions → GHCR CI/CD | ✅ Done |
| RunPod GPU workers (embed + NER) | ✅ Done |
| Standalone classroom sync script | ✅ Done |
| Visual Intelligence (CLIP + OCR) | ⏸ Postponed |
| Discord Bot | 🔲 Not started |
