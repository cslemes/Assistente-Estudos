import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


def extract_slide_texts(pptx_path: str) -> list[dict]:
    from pptx import Presentation

    prs = Presentation(pptx_path)
    result = []
    for i, slide in enumerate(prs.slides):
        parts = [
            shape.text_frame.text
            for shape in slide.shapes
            if shape.has_text_frame
        ]
        text = " ".join(parts).strip()
        result.append({"slide_index": i, "text": text})
    return result


def load_slide_frames(frames_dir: str) -> list[dict]:
    classifications_path = Path(frames_dir) / "classifications.json"
    if not classifications_path.exists():
        raise FileNotFoundError(f"No classifications.json in {frames_dir}")
    entries = json.loads(classifications_path.read_text())
    return [e for e in entries if e.get("classification") == "slide"]


def frame_number_to_timestamp(frame_name: str, interval: int) -> int:
    match = re.search(r"frame_(\d+)", frame_name)
    number = int(match.group(1))
    return (number - 1) * interval


def render_slides_to_png(pptx_path: str, output_dir: str) -> list[str] | None:
    try:
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "png",
                "--outdir",
                output_dir,
                pptx_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            return None
    except subprocess.CalledProcessError:
        return None

    pngs = sorted(Path(output_dir).glob("*.png"))
    return [str(p) for p in pngs]


def _embed_image(path: str, classifier) -> "torch.Tensor":
    import torch

    inputs = classifier.processor(images=path, return_tensors="pt")
    emb = classifier.model.get_image_features(**inputs)
    norm = emb.norm(dim=-1, keepdim=True)
    return emb / norm if norm.item() > 0 else emb


def match_slides_to_frames(
    slide_pngs: list[str],
    slide_frames: list[dict],
    classifier,
    interval: int = 5,
) -> list[dict]:
    import torch

    results = []
    for slide_index, slide_png in enumerate(slide_pngs):
        slide_emb = _embed_image(slide_png, classifier)

        best_score = -1.0
        best_frame = None
        for frame in slide_frames:
            frame_emb = _embed_image(frame["frame_path"], classifier)
            score = float(torch.nn.functional.cosine_similarity(slide_emb, frame_emb).item())
            if score > best_score:
                best_score = score
                best_frame = frame

        if best_frame is not None:
            results.append({
                "slide_index": slide_index,
                "frame_path": best_frame["frame_path"],
                "start_time": frame_number_to_timestamp(best_frame["frame"], interval),
                "similarity": best_score,
            })

    return results


def ingest_pptx(
    pptx_path: str,
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
    from app.services.clip_classifier import CLIPFrameClassifier

    collection_name = collection_name or os.getenv("COLLECTION_NAME", "aulas")

    slide_texts = extract_slide_texts(pptx_path)
    slide_frames = load_slide_frames(frames_dir)

    if not slide_frames:
        return {"ingested": 0, "message": "No slide frames found in classifications"}

    classifier = CLIPFrameClassifier(
        model_name="openai/clip-vit-base-patch16",
        device="cpu",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        pngs = render_slides_to_png(pptx_path, tmp_dir)
        if not pngs:
            return {"ingested": 0, "message": "LibreOffice rendering failed"}

        matches = match_slides_to_frames(pngs, slide_frames, classifier, interval=interval)

    class_meta = _extract_class_meta(video_path)
    embedding_models = _get_embedding_models()
    ner_pipeline = _get_ner_pipeline()
    client = _get_qdrant_client()

    slide_text_map = {s["slide_index"]: s["text"] for s in slide_texts}
    points = []
    for match in matches:
        idx = match["slide_index"]
        text = slide_text_map.get(idx, "")
        if not text.strip():
            continue
        payload = {
            "source_type": "slide",
            "file_path": pptx_path,
            "video_url": _build_deep_link(None, match["start_time"]),
            "slide_index": idx,
            "start_time": match["start_time"],
            **class_meta,
        }
        points.append(_build_point(text, embedding_models, ner_pipeline, payload))

    if points:
        upload_in_batches(client, collection_name, points)

    return {"ingested": len(points)}
