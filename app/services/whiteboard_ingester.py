import json
import os
from pathlib import Path

from app.services.notebook_matcher import ocr_frame
from app.services.slide_matcher import frame_number_to_timestamp


def load_whiteboard_frames(frames_dir: str) -> list[dict]:
    classifications_path = Path(frames_dir) / "classifications.json"
    if not classifications_path.exists():
        raise FileNotFoundError(f"No classifications.json in {frames_dir}")
    entries = json.loads(classifications_path.read_text())
    return [e for e in entries if e.get("classification") == "whiteboard"]


def frames_to_chunks(
    whiteboard_frames: list[dict],
    ocr_reader,
    interval: int = 5,
) -> list[dict]:
    chunks = []
    for frame in whiteboard_frames:
        text = ocr_frame(frame["frame_path"], ocr_reader)
        if not text.strip():
            continue
        chunks.append({
            "frame_path": frame["frame_path"],
            "start_time": frame_number_to_timestamp(frame["frame"], interval),
            "text": text,
        })
    return chunks


def ingest_whiteboard(
    video_path: str,
    frames_dir: str,
    interval: int = 5,
    collection_name: str = None,
) -> dict:
    from app.services.ingestion import (
        _build_point,
        _build_deep_link,
        _extract_class_meta,
        _get_embedding_models,
        _get_ner_pipeline,
        upload_in_batches,
        _get_qdrant_client,
    )

    collection_name = collection_name or os.getenv("COLLECTION_NAME", "aulas")

    whiteboard_frames = load_whiteboard_frames(frames_dir)
    if not whiteboard_frames:
        return {"ingested": 0, "message": "No whiteboard frames found in classifications"}

    import easyocr
    ocr_reader = easyocr.Reader(["pt", "en"], gpu=False)

    chunks = frames_to_chunks(whiteboard_frames, ocr_reader, interval=interval)
    if not chunks:
        return {"ingested": 0, "message": "No text extracted from whiteboard frames"}

    class_meta = _extract_class_meta(video_path)
    embedding_models = _get_embedding_models()
    ner_pipeline = _get_ner_pipeline()
    client = _get_qdrant_client()

    points = []
    for chunk in chunks:
        payload = {
            "source_type": "whiteboard",
            "file_path": chunk["frame_path"],
            "video_url": _build_deep_link(None, chunk["start_time"]),
            "start_time": chunk["start_time"],
            **class_meta,
        }
        points.append(_build_point(chunk["text"], embedding_models, ner_pipeline, payload))

    upload_in_batches(client, collection_name, points)
    return {"ingested": len(points)}
