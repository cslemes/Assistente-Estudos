# Aluno-Assistente (Full Jamworks Clone)

Sistema de inteligência acadêmica ponta a ponta para captura, processamento e recuperação de conhecimento de aulas da **Pós-Graduação em IA na PUC-Rio**.

## Arquitetura de Features (Mapping Jamworks)

O projeto replica as seis colunas principais de inteligência da interface original:

### 1. Transcripts & Search (RAG)

* **Engine:** Transcrição via **Deepgram Nova-3** com diarização de falantes.
* **Busca:** Armazenamento de chunks no **Qdrant Cloud** com embeddings da OpenAI.
* **Deep Link:** Cada trecho recuperado no Discord aponta para o segundo exato no YouTube (`?t=X`).

### 2. Highlights & Key Points

* **Inteligência:** LLM analisa a transcrição para identificar picos de densidade de informação.
* **Estrutura:** Geração automática de títulos e descrições para momentos-chave.
* **Navegação:** Botões no Discord que funcionam como "capítulos" do vídeo.

### 3. Visual Intelligence (CLIP + OCR Pipeline)

* **Frame Extraction:** FFmpeg extrai frames do vídeo a cada N segundos.
* **Frame Classification:** CLIP zero-shot classifica cada frame como `slide`, `notebook`, `whiteboard` ou `camera`.
* **Slide Matching:** LibreOffice renderiza slides do `.pptx` como imagens; CLIP embedding de cada slide vs. frames classificados → cosine similarity → timestamp exato de quando cada slide foi exibido.
* **Notebook Matching:** EasyOCR extrai texto de frames classificados como `notebook`; matched contra células do `.ipynb` por sobreposição de texto.
* **Whiteboard:** EasyOCR extrai conteúdo manuscrito de frames classificados como `whiteboard` → novo chunk (`source_type=whiteboard`) com timestamp.
* **Payload unificado:** todos os chunks compartilham o mesmo schema no Qdrant com `source_type`, `start_time`, `video_url` (`?t=X`) e `slide_thumb`.

### 4. Summary & Notes

* **Resumo:** Técnica de *Map-Reduce* para consolidar aulas de 3 horas em um guia de estudo executivo.
* **Notes:** Sistema de anotações temporais via Threads do Discord, permitindo que o usuário adicione observações vinculadas ao tempo do vídeo.

### 5. Flashcards (Anki Integration)

* **Automação:** Extração de conceitos atômicos para gerar decks `.apkg` via `genanki`.
* **Estudo Ativo:** Suporte a Cloze Deletions e fórmulas em LaTeX.


## Stack Cloud (Serverless First)

* **Compute:** Google Cloud Run (Orquestração de Workers Python).
* **Vector DB:** Qdrant Cloud (Memória Semântica).
* **Storage:** Cloudflare R2 (Hospedagem de áudio Opus e imagens de slides com Zero Egress).
* **Video:** YouTube API (Hosting gratuito de vídeos não listados).


## Esquema de Dados (Qdrant Payload)

Cada entrada no banco de vetores contém o contexto completo para replicar a UI:

```json
{
  "text": "Conteúdo do trecho...",
  "source_type": "transcript | slide | notebook",
  "start_time": 348,
  "video_url": "https://youtu.be/ID?t=348",
  "slide_index": 4,
  "slide_thumb": "https://r2.cloudflare.com/slide_0548.jpg",
  "topic": "Autoencoder",
  "course": "DL Python 25.1",
  "entities": {}
}
```

## Fluxo do Usuário (Discord Interface)

1. **Sync:** O bot detecta nova aula no Classroom e inicia o pipeline.
2. **Notify:** O bot posta o **Summary** e abre uma **Thread** com os **Highlights**.
3. **Interact:** O usuário faz perguntas no chat e recebe respostas baseadas nos slides e na fala do professor.


## Project Structure (Current)

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
    ├── llm_client.py        # Provider-agnostic chat client factory
    ├── ingestion.py         # Embed + NER + upload to Qdrant (transcript)
    ├── summarizer.py        # Map-Reduce summarization
    ├── flashcard_service.py # Anki .apkg generation via genanki
    ├── frame_extractor.py   # FFmpeg → frames every Ns
    ├── clip_classifier.py   # CLIP zero-shot: slide/notebook/whiteboard/camera
    ├── slide_matcher.py     # LibreOffice render + CLIP similarity → timestamp [PLANNED]
    ├── ocr.py               # EasyOCR wrapper for notebook/whiteboard frames [PLANNED]
    ├── whiteboard.py        # Whiteboard frames → text chunks → Qdrant [PLANNED]
    ├── notebook.py          # .ipynb cells + OCR match → Qdrant [PLANNED]
    └── create_collection.py # One-time Qdrant collection setup
scripts/
    ├── rename_videos.py        # Rename videos to Aula_NN_Topic.mp4
    ├── transcribe_folder.py    # Scan folder → POST /transcribe for each video
    └── cleanup.py              # Reset ai_data/ and DB records
main.py                      # CLI trigger
```


## Running the Server

```bash
uvicorn app.api:app --reload
```

> Note: changed from `uvicorn api:app` after package restructure.


## REST API Endpoints

```text
GET  /health
GET  /status
POST /sync                         # Download from Classroom
POST /scrape                       # Download from Drive/Forms URL
POST /transcribe                   # Deepgram transcription
POST /extract-audio                # FFmpeg audio extraction (single)
POST /extract-audio/batch          # FFmpeg audio extraction (batch)
POST /extract-frames               # FFmpeg frame extraction (single)
POST /extract-frames/batch         # FFmpeg frame extraction (batch)
POST /classify-frames              # CLIP zero-shot frame classification (single)
POST /classify-frames/batch        # CLIP zero-shot frame classification (batch)
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
GET  /summarize                    # List all transcriptions with summary status
POST /summarize/{id}               # Map-Reduce summarize one transcription
POST /summarize/all                # Map-Reduce summarize all pending
POST /flashcards/generate          # Generate Anki .apkg deck
```
## Pipeline Flow

```text
POST /sync              → Downloads files from Google Classroom
POST /extract-audio     → FFmpeg: video → .mp3 in ai_data/
POST /transcribe        → Deepgram → .txt + .json (utterances) + SQLite (status=pending)
POST /ingest            → NER + embed transcripts → Qdrant (status=sent)
POST /summarize/{id}    → Map-Reduce → summary stored in SQLite
POST /extract-frames    → FFmpeg: video → ai_data/{stem}_frames/frame_XXXX.jpg
POST /classify-frames   → CLIP: frames → classifications.json (slide/notebook/whiteboard/camera)
POST /ingest/slides     → LibreOffice render + CLIP similarity → timestamp → Qdrant [PLANNED]
POST /ingest/notebook   → EasyOCR → cell match → Qdrant [PLANNED]
POST /ingest/whiteboard → EasyOCR → Qdrant [PLANNED]
POST /ask               → Query → hybrid search → LLM → answer
POST /flashcards/generate → Qdrant chunks → LLM → Anki .apkg
```

## Implementation Status

| Feature | Status |
| --------- | -------- |
| Transcripts & Search (RAG) | Implemented |
| SQLite staging DB (pending → embedded → sent) | Implemented |
| NER enrichment (`lfcc/bert-portuguese-ner`) | Implemented |
| Utterance-level chunking with timestamps | Implemented |
| Qdrant Cloud — ingestion + retrieval | Implemented |
| Hybrid search (dense + BM25 + ColBERT rerank) | Implemented |
| Streaming RAG (SSE) | Implemented |
| Google Classroom sync (with download manifest) | Implemented |
| Deepgram Nova-3 PT-BR diarization | Implemented |
| YouTube resumable upload (auto token refresh) | Implemented |
| Groq LLM (llama-3.3-70b) sync + streaming | Implemented |
| FFmpeg audio extraction endpoint | Implemented |
| Summary / Map-Reduce (`summarizer.py`) | Implemented |
| Flashcards (Anki/genanki) | Implemented |
| Frame extraction (FFmpeg) | Implemented |
| CLIP zero-shot frame classifier (`openai/clip-vit-base-patch16`) | Implemented |
| PowerPoint ingestion — LibreOffice render + CLIP similarity matching | Planned |
| Jupyter notebook ingestion — EasyOCR + cell text match | Planned |
| Whiteboard ingestion — EasyOCR → Qdrant chunks | Planned |
| Slide thumbnail capture + R2 upload | Planned |
| Discord Bot | Not started |
| Highlights / Key Points | Not started |

---

## External Services

| Service | Purpose | Status |
| --------- | --------- | -------- |
| Deepgram Nova-3 | Speech-to-text (PT-BR) + diarization | Implemented |
| Google Classroom API | Courses, topics, assignments | Implemented |
| Google Drive API | File download/listing | Implemented |
| YouTube Data API | Unlisted video upload | Implemented |
| Playwright/Chromium | Google Forms scraping | Implemented |
| FFmpeg | Audio extraction + frame extraction | Implemented |
| Qdrant Cloud | Vector DB for RAG search | Implemented |
| OpenAI GPT-4o-mini | RAG answer generation | Implemented |
| Groq (llama-3.3-70b) | RAG answer generation (fast/free) | Implemented |
| CLIP (`openai/clip-vit-base-patch16`) | Zero-shot frame classification | Implemented |
| Anki/genanki | Flashcard .apkg generation | Implemented |
| LibreOffice headless | Render .pptx slides → PNG images | Planned |
| python-pptx | PowerPoint slide text extraction | Planned |
| EasyOCR | Notebook + whiteboard text extraction from frames | Planned |
| Cloudflare R2 | Slide thumbnail storage | Planned |
| Discord Bot | User interface | Not started |
