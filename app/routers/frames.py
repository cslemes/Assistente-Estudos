import json
import os
from collections import Counter
from functools import lru_cache

from fastapi import APIRouter, HTTPException

from app.config.settings import Settings
from app.models.api import (
    ClassifyFramesBatchRequest,
    ClassifyFramesRequest,
    ExtractFramesBatchRequest,
    ExtractFramesRequest,
)
from app.config.settings import VIDEO_EXTENSIONS
from app.services.clip_classifier import CLIPFrameClassifier, get_classifier
from app.services.frame_extractor import extract_frames_from_video

router = APIRouter(tags=["frames"])


def _frames_dir(video_path: str) -> str:
    stem = os.path.splitext(os.path.basename(video_path))[0]
    ai_data_dir = os.path.join(os.path.dirname(os.path.dirname(video_path)), "ai_data")
    return os.path.join(ai_data_dir, f"{stem}_frames")


@router.post("/extract-frames")
def extract_frames_job(payload: ExtractFramesRequest):
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    frames_dir = _frames_dir(payload.file_path)
    frames = extract_frames_from_video(payload.file_path, frames_dir, payload.interval)
    if frames is None:
        raise HTTPException(status_code=500, detail="FFmpeg frame extraction failed")

    return {
        "file_path": payload.file_path,
        "frames_dir": frames_dir,
        "frame_count": len(frames),
    }


@router.post("/extract-frames/batch")
def extract_frames_batch(payload: ExtractFramesBatchRequest):
    if not os.path.isdir(payload.folder):
        raise HTTPException(status_code=404, detail="Folder not found")

    files = []
    walk = (
        os.walk(payload.folder)
        if payload.recursive
        else [(payload.folder, [], os.listdir(payload.folder))]
    )
    for dirpath, _, filenames in walk:
        for fname in filenames:
            if fname.lower().endswith(VIDEO_EXTENSIONS):
                files.append(os.path.join(dirpath, fname))
    files.sort()

    results = []
    skipped = []
    failed = []

    for video_path in files:
        frames_dir = _frames_dir(video_path)
        # Skip if frames already extracted
        if os.path.isdir(frames_dir) and os.listdir(frames_dir):
            skipped.append(video_path)
            continue

        frames = extract_frames_from_video(video_path, frames_dir, payload.interval)
        if frames:
            results.append({"video": video_path, "frames_dir": frames_dir, "frame_count": len(frames)})
        else:
            failed.append(video_path)

    return {
        "processed": len(results),
        "skipped": len(skipped),
        "failed": len(failed),
        "files": results,
        "errors": failed,
    }


def _get_classifier() -> CLIPFrameClassifier:
    return get_classifier()


@router.post("/classify-frames")
def classify_frames_job(payload: ClassifyFramesRequest):
    if not os.path.isdir(payload.frames_dir):
        raise HTTPException(status_code=404, detail="Frames directory not found")

    results = _get_classifier().classify_directory(payload.frames_dir)

    out = os.path.join(payload.frames_dir, "classifications.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    counts = dict(Counter(r["classification"] for r in results))
    return {
        "frames_dir": payload.frames_dir,
        "total_frames": len(results),
        "counts": counts,
        "output_file": out,
    }


@router.post("/classify-frames/batch")
def classify_frames_batch(payload: ClassifyFramesBatchRequest):
    # Find all *_frames/ directories under the given folder
    frames_dirs = []
    walk = os.walk(payload.folder) if payload.recursive else [(payload.folder, os.listdir(payload.folder), [])]
    for dirpath, dirnames, _ in walk:
        for name in dirnames:
            if name.endswith("_frames"):
                frames_dirs.append(os.path.join(dirpath, name))

    if not frames_dirs:
        raise HTTPException(status_code=404, detail="No *_frames directories found")

    classifier = _get_classifier()
    results = []
    skipped = []
    failed = []

    for frames_dir in sorted(frames_dirs):
        out = os.path.join(frames_dir, "classifications.json")
        if os.path.exists(out):
            skipped.append(frames_dir)
            continue
        try:
            classifications = classifier.classify_directory(frames_dir)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(classifications, f, indent=2, ensure_ascii=False)
            counts = dict(Counter(r["classification"] for r in classifications))
            results.append({"frames_dir": frames_dir, "total_frames": len(classifications), "counts": counts})
        except Exception as e:
            failed.append({"frames_dir": frames_dir, "error": str(e)})

    return {
        "processed": len(results),
        "skipped": len(skipped),
        "failed": len(failed),
        "results": results,
        "errors": failed,
    }
