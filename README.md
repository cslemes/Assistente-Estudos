# Academic Assistant (Jamworks Clone)

End-to-end academic intelligence system for capturing, processing, and retrieving knowledge from classes at the **AI Post-Graduation Program at PUC-Rio**.

## Feature Architecture (Jamworks Mapping)

The project replicates the six main intelligence columns of the original interface:

### 1. Transcripts & Search (RAG)

* **Engine:** Transcription via **Deepgram Nova-3** with speaker diarization.
* **Search:** Chunk storage in **Qdrant Cloud** with OpenAI embeddings.
* **Deep Link:** Each retrieved excerpt points to the exact second on YouTube (`?t=X`).

### 2. Highlights & Key Points

* **Intelligence:** LLM analyzes the transcript to identify information density peaks.
* **Structure:** Automatic generation of titles and descriptions for key moments.
* **Navigation:** Discord buttons that work as video "chapters".

### 3. Visual Intelligence (CLIP + OCR Pipeline)

* **Frame Extraction:** FFmpeg extracts frames from the video every N seconds.
* **Frame Classification:** CLIP zero-shot classifies each frame as `slide`, `notebook`, `whiteboard`, or `camera`.
* **Slide Matching:** LibreOffice renders `.pptx` slides as images; CLIP embedding of each slide vs. classified frames → cosine similarity → exact timestamp when each slide was shown.
* **Notebook Matching:** EasyOCR extracts text from frames classified as `notebook`; matched against `.ipynb` cells by text overlap.
* **Whiteboard:** EasyOCR extracts handwritten content from frames classified as `whiteboard` → new chunk (`source_type=whiteboard`) with timestamp.
* **Unified payload:** all chunks share the same schema in Qdrant with `source_type`, `start_time`, `video_url` (`?t=X`), and `slide_thumb`.

### 4. Summary & Notes

* **Summary:** *Map-Reduce* technique to condense 3-hour classes into an executive study guide.
* **Notes:** Temporal annotation system via Discord Threads, allowing users to add observations linked to the video timestamp.

### 5. Flashcards (Anki Integration)

* **Automation:** Extraction of atomic concepts to generate `.apkg` decks via `genanki`.
* **Active Study:** Support for Cloze Deletions and LaTeX formulas.

---

## Cloud Stack (Serverless First)

* **Compute:** Google Cloud Run (Python Worker Orchestration).
* **Vector DB:** Qdrant Cloud (Semantic Memory).
* **Storage:** Cloudflare R2 (Opus audio and slide image hosting with Zero Egress).
* **Video:** YouTube API (Free hosting for unlisted videos).

---

## Data Schema (Qdrant Payload)

Each vector database entry contains the full context needed to replicate the UI:

```json
{
  "text": "Chunk content...",
  "source_type": "transcript | slide | notebook | whiteboard",
  "start_time": 348,
  "video_url": "https://youtu.be/ID?t=348",
  "slide_index": 4,
  "slide_thumb": "https://r2.cloudflare.com/slide_0548.jpg",
  "topic": "Autoencoder",
  "course": "DL Python 25.1",
  "aula_number": 7,
  "entities": {}
}
```

---

## User Flow (Discord Interface)

1. **Sync:** The bot detects a new class in Classroom and starts the pipeline.
2. **Notify:** The bot posts the **Summary** and opens a **Thread** with the **Highlights**.
3. **Interact:** The user asks questions in chat and receives answers grounded in slides and the professor's speech.

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
│   └── groq.py              # POST /ask/groq, POST /ask/groq/stream
└── services/
    ├── sync.py              # Google Classroom → Drive download
    ├── drive.py             # Drive/Forms scraping + file org
    ├── transcription.py     # Deepgram Nova-3 PT-BR + diarization
    ├── youtube.py           # YouTube resumable upload
    ├── embedder.py          # Hybrid query embedder
    ├── retriever.py         # Qdrant 2-stage retrieval
    ├── openai_service.py    # OpenAI sync + streaming
    ├── groq_service.py      # Groq sync + streaming
    ├── ingestion.py         # Embed + NER + upload to Qdrant (transcript)
    ├── frame_extractor.py   # FFmpeg → frames every Ns [PLANNED]
    ├── clip_classifier.py   # CLIP zero-shot: slide/notebook/whiteboard/camera [PLANNED]
    ├── slide_matcher.py     # LibreOffice render + CLIP similarity → timestamp [PLANNED]
    ├── ocr.py               # EasyOCR wrapper for notebook/whiteboard frames [PLANNED]
    ├── whiteboard.py        # Whiteboard frames → text chunks → Qdrant [PLANNED]
    ├── notebook.py          # .ipynb cells + OCR match → Qdrant [PLANNED]
    └── create_collection.py # One-time Qdrant collection setup
scripts/
    ├── rename_videos.py     # Rename videos to Aula_NN_Topic.mp4
    ├── transcribe_folder.py # Batch audio extract + transcribe
    └── cleanup.py           # Reset ai_data/ and DB records
streamlit_app.py             # Chat UI
main.py                      # CLI trigger
```

---

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Python 3.13+
- A `.env` file with the required credentials (see `.env.template`)

### Install dependencies

```bash
uv sync
```

### Environment variables

Copy `.env.template` to `.env` and fill in the values:

```bash
cp .env.template .env
```

Required keys:

| Variable | Description | Get it |
|----------|-------------|--------|
| `OPENAI_API_KEY` | OpenAI API key | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `GROQ_API_KEY` | Groq API key | [console.groq.com/keys](https://console.groq.com/keys) |
| `QDRANT_URL` | Qdrant Cloud cluster URL | [cloud.qdrant.io](https://cloud.qdrant.io) |
| `QDRANT_API_KEY` | Qdrant Cloud API key | [cloud.qdrant.io](https://cloud.qdrant.io) |
| `DEEPGRAM_API_KEY` | Deepgram API key | [console.deepgram.com](https://console.deepgram.com) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | [console.cloud.google.com](https://console.cloud.google.com) — see GCP Setup below |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | [console.cloud.google.com](https://console.cloud.google.com) — see GCP Setup below |
| `YOUTUBE_CHANNEL_ID` | Target YouTube channel | [youtube.com/account_advanced](https://www.youtube.com/account_advanced) |

---

## Google Cloud Platform (GCP) Setup

The sync pipeline requires a GCP OAuth 2.0 desktop client with four APIs enabled.

### 1. Create a GCP Project

Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project (e.g. `Academic-Assistant`).

### 2. Enable the required APIs

In **APIs & Services → Library**, enable all four:

| API | Used for |
|-----|----------|
| **Google Classroom API** | List courses, topics, assignments (`courseWork`) and materials (`courseWorkMaterials`) |
| **Google Drive API** | Download attached files and traverse shared folders |
| **YouTube Data API v3** | Upload class recordings as unlisted videos |
| **Google Forms API** | *(optional)* — forms are scraped via Playwright; the API is not called directly |

### 3. Configure the OAuth consent screen

Go to **APIs & Services → OAuth consent screen**:

- User type: **External** (or Internal if using a Google Workspace org account)
- Add the following scopes — these are the exact OAuth scopes the app requests at login:

```
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly
https://www.googleapis.com/auth/classroom.coursework.me.readonly
https://www.googleapis.com/auth/classroom.announcements.readonly
https://www.googleapis.com/auth/classroom.topics.readonly
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/youtube.upload
```

- Add your Google account as a **test user** (required while the app is in testing status).

### 4. Create OAuth credentials

Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**:

- Application type: **Desktop app**
- Download the JSON file and save it as **`credentials.json`** in the project root.

### 5. First-time authentication

On the first run of `POST /sync`, the app opens a browser window asking you to log in and grant permissions. After approval, a `token.json` file is saved locally and reused on subsequent runs.

```
project root/
├── credentials.json   ← downloaded from GCP (do not commit)
└── token.json         ← auto-generated after first login (do not commit)
```

> Both files are sensitive and are already listed in `.gitignore`.

---

## Running the API Server

```bash
uv run uvicorn app.api:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## Running the Chat UI (Streamlit)

With the API server already running, open a second terminal:

```bash
uv run streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser.

**Features:**
- Select LLM provider (Groq — fast, or OpenAI — precise)
- Filter answers by course and topic
- Streaming responses with source citations and YouTube deep links

---

## REST API Endpoints

```text
GET  /health
GET  /status
GET  /classes                      # List indexed classes
POST /sync                         # Download from Classroom
POST /scrape                       # Download from Drive/Forms URL
POST /transcribe                   # Deepgram transcription
POST /extract-audio                # FFmpeg audio extraction (single)
POST /extract-audio/batch          # FFmpeg audio extraction (batch)
POST /upload                       # Upload single video to YouTube
POST /upload/batch?limit=6         # Batch upload (default 6/day)
POST /ingest                       # Embed + NER + send to Qdrant (transcripts)
POST /ingest/slides                # CLIP match pptx slides → Qdrant [PLANNED]
POST /ingest/notebook              # CLIP/OCR match .ipynb cells → Qdrant [PLANNED]
POST /ingest/whiteboard            # OCR whiteboard frames → Qdrant [PLANNED]
GET  /transcriptions/pending       # List pending for embedding
PATCH /transcriptions/{id}/status  # Update status
POST /search                       # Hybrid vector search
POST /ask                          # RAG answer (sync, OpenAI)
POST /ask/stream                   # RAG answer (SSE streaming, OpenAI)
POST /ask/groq                     # RAG answer (sync, Groq)
POST /ask/groq/stream              # RAG answer (SSE streaming, Groq)
```

---

## Pipeline Flow

```text
POST /sync              → Download files from Google Classroom
POST /extract-audio     → FFmpeg: video → .mp3 in ai_data/
POST /transcribe        → Deepgram → .txt + .json (utterances) + SQLite (status=pending)
POST /ingest            → NER + embed transcripts → Qdrant (status=sent)
POST /ingest/slides     → frames → CLIP classify → LibreOffice render → CLIP similarity → timestamp → Qdrant [PLANNED]
POST /ingest/notebook   → frames → CLIP classify → EasyOCR → cell match → Qdrant [PLANNED]
POST /ingest/whiteboard → frames → CLIP classify → EasyOCR → Qdrant [PLANNED]
POST /ask               → Query → hybrid search → LLM → answer
```

---

## Implementation Status

| Feature | Status |
| --------- | -------- |
| Transcripts & Search (RAG) | ✅ Implemented |
| SQLite staging DB (pending → embedded → sent) | ✅ Implemented |
| NER enrichment (`lfcc/bert-portuguese-ner`) | ✅ Implemented |
| Utterance-level chunking with timestamps | ✅ Implemented |
| Qdrant Cloud — ingestion + retrieval | ✅ Implemented |
| Hybrid search (dense + BM25 + ColBERT rerank) | ✅ Implemented |
| Streaming RAG (SSE) | ✅ Implemented |
| Google Classroom sync (with download manifest) | ✅ Implemented |
| Deepgram Nova-3 PT-BR diarization | ✅ Implemented |
| YouTube resumable upload (auto token refresh) | ✅ Implemented |
| Groq LLM (llama-3.3-70b) sync + streaming | ✅ Implemented |
| FFmpeg audio extraction endpoint | ✅ Implemented |
| Streamlit chat UI | ✅ Implemented |
| Frame extraction (FFmpeg) | 🔜 Planned |
| CLIP zero-shot frame classifier (slide/notebook/whiteboard/camera) | 🔜 Planned |
| PowerPoint ingestion — LibreOffice render + CLIP similarity matching | 🔜 Planned |
| Jupyter notebook ingestion — EasyOCR + cell text match | 🔜 Planned |
| Whiteboard ingestion — EasyOCR → Qdrant chunks | 🔜 Planned |
| Slide thumbnail capture + R2 upload | 🔜 Planned |
| Discord Bot | ❌ Not started |
| Highlights / Key Points | ❌ Not started |
| Summary / Map-Reduce | ❌ Not started |
| Flashcards (Anki/genanki) | ❌ Not started |

---

## External Services

| Service | Purpose | Status |
| --------- | --------- | -------- |
| Deepgram Nova-3 | Speech-to-text (PT-BR) + diarization | ✅ Implemented |
| Google Classroom API | Courses, topics, assignments | ✅ Implemented |
| Google Drive API | File download/listing | ✅ Implemented |
| YouTube Data API | Unlisted video upload | ✅ Implemented |
| Playwright/Chromium | Google Forms scraping | ✅ Implemented |
| FFmpeg | Audio extraction + frame extraction | ✅ Implemented (frames planned) |
| Qdrant Cloud | Vector DB for RAG search | ✅ Implemented |
| OpenAI GPT-4o-mini | RAG answer generation | ✅ Implemented |
| Groq (llama-3.3-70b) | RAG answer generation (fast) | ✅ Implemented |
| CLIP (`open_clip`) | Zero-shot frame classification + slide similarity | 🔜 Planned |
| LibreOffice headless | Render .pptx slides → PNG images | 🔜 Planned |
| python-pptx | PowerPoint slide text extraction | 🔜 Planned |
| EasyOCR | Notebook + whiteboard text extraction from frames | 🔜 Planned |
| Cloudflare R2 | Slide thumbnail storage | 🔜 Planned |
| Discord Bot | User interface | ❌ Not started |
| Anki/genanki | Flashcard generation | ❌ Not started |
