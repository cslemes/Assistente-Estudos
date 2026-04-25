import json
import os
import uuid
from functools import lru_cache

from tqdm.auto import tqdm

from app.database import get_pending, set_status


EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
NER_MODEL_ID = "lfcc/bert-portuguese-ner"
MIN_ENTITY_CONFIDENCE = 0.80
CHUNK_SIZE = 750  # characters
WINDOW_SECONDS = 60  # legacy word-level chunking window


def _get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )


@lru_cache(maxsize=1)
def _get_ner_pipeline():
    import torch
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline      
    device = 0 if torch.cuda.is_available() else -1
    tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_ID)
    model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_ID)
    
    return pipeline(
        "ner", 
        model=model, 
        tokenizer=tokenizer, 
        aggregation_strategy="first",
        device=device  # THIS IS THE KEY
    )

@lru_cache(maxsize=1)
def _get_embedding_models():
    from fastembed import TextEmbedding
    from fastembed.sparse.bm25 import Bm25
    from fastembed.late_interaction import LateInteractionTextEmbedding
    dense_model = TextEmbedding(EMBED_MODEL_ID)
    bm25_model = Bm25("Qdrant/bm25")
    colbert_model = LateInteractionTextEmbedding("colbert-ir/colbertv2.0")
    return dense_model, bm25_model, colbert_model


def extract_entities(text: str, ner_pipeline) -> dict:
    if len(text) > 5000:
        text = text[:5000]

    raw = ner_pipeline(text)
    entities = {}
    for ent in raw:
        if len(ent["word"]) < 2 and not ent["word"].isupper():
            continue
        if ent.get("score", 0) < MIN_ENTITY_CONFIDENCE:
            continue
        entity_type = ent["entity_group"]
        entities.setdefault(entity_type, set()).add(ent["word"])

    return {k: list(v) for k, v in entities.items()}


def create_embeddings(text: str, dense_model, bm25_model, colbert_model) -> dict:
    dense = list(dense_model.passage_embed([text]))[0].tolist()
    sparse = list(bm25_model.passage_embed([text]))[0].as_object()
    colbert = list(colbert_model.passage_embed([text]))[0].tolist()
    return {"dense": dense, "sparse": sparse, "colbertv2.0": colbert}


def chunk_segments(items: list, max_chars: int = CHUNK_SIZE) -> list:
    """
    Chunk transcription data into RAG chunks.

    Supports two formats:
    - Utterance format {"text", "start", "end", "speaker"}: merges consecutive
      same-speaker utterances while under max_chars. Speaker change forces a new chunk.
    - Word-level format {"word", "start", "end", "speaker"} (legacy): groups words
      into fixed 60-second time windows.

    Returns: list of {"text": str, "start": int}
    """
    if not items:
        return []

    if "text" in items[0]:
        return _chunk_utterances(items, max_chars)
    return _chunk_legacy_words(items)


def _chunk_utterances(items: list, max_chars: int) -> list:
    chunks = []
    acc_text = items[0]["text"]
    acc_start = items[0]["start"]
    acc_speaker = items[0]["speaker"]

    for utt in items[1:]:
        merged = acc_text + " " + utt["text"]
        if utt["speaker"] == acc_speaker and len(merged) <= max_chars:
            acc_text = merged
        else:
            chunks.append({"text": acc_text, "start": int(acc_start)})
            acc_text = utt["text"]
            acc_start = utt["start"]
            acc_speaker = utt["speaker"]

    chunks.append({"text": acc_text, "start": int(acc_start)})
    return chunks


def _chunk_legacy_words(items: list) -> list:
    chunks = []
    window_start = items[0]["start"]
    current_words = []

    for w in items:
        if w["start"] - window_start >= WINDOW_SECONDS and current_words:
            chunks.append({
                "text": " ".join(x["word"] for x in current_words),
                "start": int(window_start),
            })
            window_start = w["start"]
            current_words = []
        current_words.append(w)

    if current_words:
        chunks.append({
            "text": " ".join(x["word"] for x in current_words),
            "start": int(window_start),
        })
    return chunks


def _extract_class_meta(file_path: str) -> dict:
    from pathlib import PurePosixPath, PureWindowsPath
    import re
    # Paths stored in DB are Windows-style; use PureWindowsPath so backslashes parse correctly
    p = PureWindowsPath(file_path) if "\\" in file_path else PurePosixPath(file_path)
    topic = p.parent.parent.name
    course = p.parent.parent.parent.name
    m = re.search(r'[Aa]ula[_\s]*(\d+)', p.stem)
    aula_number = int(m.group(1)) if m else None
    # Part number: trailing _N suffix after the base name (0 = main video)
    part_m = re.search(r'_(\d+)$', p.stem)
    part_number = int(part_m.group(1)) if part_m else 0
    return {"topic": topic, "course": course, "aula_number": aula_number, "part_number": part_number}


def _build_deep_link(video_url: str | None, start_time: int | None) -> str | None:
    if not video_url or start_time is None:
        return video_url
    return f"{video_url.split('?')[0]}?t={start_time}"


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, current = [], ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) > chunk_size and current:
            chunks.append(current.strip())
            current = paragraph
        else:
            current += "\n" + paragraph
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _build_point(text: str, embedding_models, ner_pipeline, payload: dict):
    dense_model, bm25_model, colbert_model = embedding_models
    embeddings = create_embeddings(text, dense_model, bm25_model, colbert_model)

    entities = {}
    if len(text.split()) > 20:
        try:
            entities = extract_entities(text, ner_pipeline)
        except Exception:
            pass

    from qdrant_client.http.models import PointStruct
    return PointStruct(
        id=str(uuid.uuid4()),
        vector={
            "dense": embeddings["dense"],
            "sparse": embeddings["sparse"],
            "colbertv2.0": embeddings["colbertv2.0"],
        },
        payload={"text": text, "entities": entities, **payload},
    )


def upload_in_batches(client, collection_name: str, points: list, batch_size: int = 10):
    n_batches = (len(points) + batch_size - 1) // batch_size
    print(f"Uploading {len(points)} points in {n_batches} batches...")
    uploaded = 0
    for i in tqdm(range(0, len(points), batch_size), total=n_batches):
        batch = points[i: i + batch_size]
        try:
            client.upload_points(collection_name=collection_name, points=batch)
            uploaded += len(batch)
        except Exception as e:
            print(f"[Qdrant] Batch upload failed (batch {i // batch_size + 1}): {e}")
            raise
    print(f"Uploaded {uploaded} points to '{collection_name}'")


def _build_points_for_row(row: dict, embedding_models, ner_pipeline) -> list:
    class_meta = _extract_class_meta(row["file_path"])
    raw_segments = row.get("segments_json")

    if raw_segments:
        timed_chunks = chunk_segments(json.loads(raw_segments))
        return [
            _build_point(
                tc["text"],
                embedding_models,
                ner_pipeline,
                {
                    "source_type": "transcript",
                    "file_path": row["file_path"],
                    "video_url": _build_deep_link(row.get("video_url"), tc["start"]),
                    "transcription_id": row["id"],
                    "start_time": tc["start"],
                    **class_meta,
                },
            )
            for tc in timed_chunks
        ]

    return [
        _build_point(
            chunk,
            embedding_models,
            ner_pipeline,
            {
                "source_type": "transcript",
                "file_path": row["file_path"],
                "video_url": row.get("video_url"),
                "transcription_id": row["id"],
                **class_meta,
            },
        )
        for chunk in chunk_text(row["text"])
    ]


def ingest_pending_transcriptions(collection_name: str = None) -> dict:
    collection_name = collection_name or os.getenv("COLLECTION_NAME", "aulas")
    pending = get_pending()

    if not pending:
        return {"ingested": 0, "message": "No pending transcriptions"}

    client = _get_qdrant_client()
    embedding_models = _get_embedding_models()
    ner_pipeline = _get_ner_pipeline()

    print(f"Processing {len(pending)} transcriptions...")
    points = []
    processed_ids = []
    for row in tqdm(pending):
        points.extend(_build_points_for_row(row, embedding_models, ner_pipeline))
        processed_ids.append(row["id"])

    upload_in_batches(client, collection_name, points)

    for tid in processed_ids:
        set_status(tid, "sent")

    return {"ingested": len(processed_ids), "points_uploaded": len(points)}
