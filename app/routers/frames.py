import os

from fastapi import APIRouter, HTTPException

from app.models.api import ExtractFramesBatchRequest, ExtractFramesRequest
from app.services.frame_extractor import extract_frames_from_video

router = APIRouter(tags=["frames"])

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")


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
