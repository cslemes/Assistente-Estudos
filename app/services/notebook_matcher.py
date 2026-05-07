import json
import os
from functools import lru_cache
from pathlib import Path

from app.services.slide_matcher import frame_number_to_timestamp


@lru_cache(maxsize=1)
def _get_ocr_reader():
    import easyocr
    import torch
    gpu = torch.cuda.is_available()
    return easyocr.Reader(["pt", "en"], gpu=gpu)


def extract_notebook_cells(ipynb_path: str) -> list[dict]:
    nb = json.loads(Path(ipynb_path).read_text())
    result = []
    for i, cell in enumerate(nb.get("cells", [])):
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        text = source.strip()
        if not text:
            continue
        result.append({
            "cell_index": i,
            "cell_type": cell.get("cell_type", "code"),
            "text": text,
        })
    return result


def load_notebook_frames(frames_dir: str) -> list[dict]:
    classifications_path = Path(frames_dir) / "classifications.json"
    if not classifications_path.exists():
        raise FileNotFoundError(f"No classifications.json in {frames_dir}")
    entries = json.loads(classifications_path.read_text())
    return [e for e in entries if e.get("classification") == "notebook"]


def ocr_frame(frame_path: str, ocr_reader) -> str:
    results = ocr_reader.readtext(frame_path, detail=1)
    return " ".join(text for _, text, _ in results)


def ocr_frame_via_runpod(frame_path: str, client, endpoint_id: str) -> str:
    import base64
    with open(frame_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    result = client.call(endpoint_id, {"image_b64": image_b64})
    return result.get("text", "")


def _make_ocr_callable(settings):
    """Return a Callable[[frame_path: str], str] regardless of use_runpod."""
    if settings.use_runpod:
        from app.services.runpod_client import RunPodClient
        client = RunPodClient(settings)
        endpoint_id = settings.runpod_ocr_endpoint_id
        return lambda frame_path: ocr_frame_via_runpod(frame_path, client, endpoint_id)
    reader = _get_ocr_reader()
    return lambda frame_path: ocr_frame(frame_path, reader)


def _token_overlap(a: str, b: str) -> float:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def match_cells_to_frames(
    cells: list[dict],
    notebook_frames: list[dict],
    ocr_fn,
    interval: int = 5,
    min_overlap: float = 0.1,
) -> list[dict]:
    frame_texts = [
        (frame, ocr_fn(frame["frame_path"]))
        for frame in notebook_frames
    ]

    results = []
    for cell in cells:
        best_score = 0.0
        best_frame = None
        for frame, frame_text in frame_texts:
            score = _token_overlap(cell["text"], frame_text)
            if score > best_score:
                best_score = score
                best_frame = frame

        if best_frame is not None and best_score >= min_overlap:
            results.append({
                "cell_index": cell["cell_index"],
                "cell_type": cell["cell_type"],
                "frame_path": best_frame["frame_path"],
                "start_time": frame_number_to_timestamp(best_frame["frame"], interval),
                "overlap": best_score,
            })

    return results


def ingest_notebook(
    ipynb_path: str,
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

    cells = extract_notebook_cells(ipynb_path)
    notebook_frames = load_notebook_frames(frames_dir)

    if not notebook_frames:
        return {"ingested": 0, "message": "No notebook frames found in classifications"}

    ocr_fn = _make_ocr_callable(settings)
    matches = match_cells_to_frames(cells, notebook_frames, ocr_fn, interval=interval)

    if not matches:
        return {"ingested": 0, "message": "No cells matched to frames"}

    class_meta = _extract_class_meta(video_path)
    if settings.use_runpod:
        embedding_arg = settings
        ner_arg = settings
    else:
        embedding_arg = _get_embedding_models()
        ner_arg = _get_ner_pipeline()
    client = _get_qdrant_client()
    video_url = get_video_url_by_video_path(video_path)

    cell_text_map = {c["cell_index"]: c["text"] for c in cells}
    points = []
    for match in matches:
        text = cell_text_map.get(match["cell_index"], "")
        payload = {
            "source_type": "notebook",
            "file_path": ipynb_path,
            "video_url": _build_deep_link(video_url, match["start_time"]),
            "cell_index": match["cell_index"],
            "cell_type": match["cell_type"],
            "start_time": match["start_time"],
            **class_meta,
        }
        points.append(_build_point(text, embedding_arg, ner_arg, payload))

    upload_in_batches(client, collection_name, points)
    return {"ingested": len(points)}
