import os

from fastapi import APIRouter, HTTPException

from app.models.api import ExtractAudioBatchRequest, ExtractAudioRequest, TranscribeRequest
from app.services.drive import extract_audio_from_video
from app.services.transcription import transcribe_file

router = APIRouter(tags=["audio"])

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")


@router.post("/transcribe")
def transcribe_file_job(payload: TranscribeRequest):
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    transcribe_file(payload.file_path)
    output_file = os.path.splitext(payload.file_path)[0] + ".txt"
    return {
        "file_path": payload.file_path,
        "output_file": output_file,
        "exists": os.path.exists(output_file),
    }


@router.post("/extract-audio")
def extract_audio_job(payload: ExtractAudioRequest):
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    video_path = payload.file_path
    stem = os.path.splitext(os.path.basename(video_path))[0]
    ai_data_dir = os.path.join(os.path.dirname(os.path.dirname(video_path)), "ai_data")
    os.makedirs(ai_data_dir, exist_ok=True)
    audio_path = os.path.join(ai_data_dir, stem + ".mp3")

    result = extract_audio_from_video(video_path, audio_path)
    if result is None:
        raise HTTPException(status_code=500, detail="FFmpeg audio extraction failed")

    return {"file_path": video_path, "audio_path": result}


@router.post("/extract-audio/batch")
def extract_audio_batch(payload: ExtractAudioBatchRequest):
    if not os.path.isdir(payload.folder):
        raise HTTPException(status_code=404, detail="Folder not found")

    files = []
    walk = os.walk(payload.folder) if payload.recursive else [(payload.folder, [], os.listdir(payload.folder))]
    for dirpath, _, filenames in walk:
        for fname in filenames:
            if fname.lower().endswith(VIDEO_EXTENSIONS):
                files.append(os.path.join(dirpath, fname))
    files.sort()

    results = []
    failed = []
    for video_path in files:
        stem = os.path.splitext(os.path.basename(video_path))[0]
        ai_data_dir = os.path.join(os.path.dirname(os.path.dirname(video_path)), "ai_data")
        os.makedirs(ai_data_dir, exist_ok=True)
        audio_path = os.path.join(ai_data_dir, stem + ".mp3")

        result = extract_audio_from_video(video_path, audio_path)
        if result:
            results.append({"video": video_path, "audio": result})
        else:
            failed.append(video_path)

    return {
        "processed": len(results),
        "failed": len(failed),
        "files": results,
        "errors": failed,
    }
