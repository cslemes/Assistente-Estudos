import json
import os
from pathlib import Path

from app.services.notebook_matcher import _make_ocr_callable
from app.services.slide_matcher import frame_number_to_timestamp


def load_whiteboard_frames(frames_dir: str) -> list[dict]:
    classifications_path = Path(frames_dir) / "classifications.json"
    if not classifications_path.exists():
        raise FileNotFoundError(f"No classifications.json in {frames_dir}")
    entries = json.loads(classifications_path.read_text())
    return [e for e in entries if e.get("classification") == "whiteboard"]


def frames_to_chunks(
    whiteboard_frames: list[dict],
    ocr_fn,
    interval: int = 5,
) -> list[dict]:
    chunks = []
    for frame in whiteboard_frames:
        text = ocr_fn(frame["frame_path"])
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
    from app.config.settings import Settings
    from app.services.ingestion import (
        _build_point,
        _build_deep_link,
        _extract_class_meta,
        _get_embedding_models,
        _get_ner_pipeline,
        upload_in_batches,
        _get_qdrant_client,
    )

    from app.database import get_video_url_by_video_path

    settings = Settings()
    collection_name = collection_name or os.getenv("COLLECTION_NAME", "aulas")

    whiteboard_frames = load_whiteboard_frames(frames_dir)
    if not whiteboard_frames:
        return {"ingested": 0, "message": "No whiteboard frames found in classifications"}

    ocr_fn = _make_ocr_callable(settings)
    chunks = frames_to_chunks(whiteboard_frames, ocr_fn, interval=interval)
    if not chunks:
        return {"ingested": 0, "message": "No text extracted from whiteboard frames"}

    class_meta = _extract_class_meta(video_path)
    if settings.use_runpod:
        embedding_arg = settings
        ner_arg = settings
    else:
        embedding_arg = _get_embedding_models()
        ner_arg = _get_ner_pipeline()
    client = _get_qdrant_client()
    video_url = get_video_url_by_video_path(video_path)

    points = []
    for chunk in chunks:
        payload = {
            "source_type": "whiteboard",
            "file_path": chunk["frame_path"],
            "video_url": _build_deep_link(video_url, chunk["start_time"]),
            "start_time": chunk["start_time"],
            **class_meta,
        }
        points.append(_build_point(chunk["text"], embedding_arg, ner_arg, payload))

    upload_in_batches(client, collection_name, points)
    return {"ingested": len(points)}
