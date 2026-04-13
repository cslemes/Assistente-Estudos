"""
Scan a folder for video files, extract audio via FFmpeg, then submit each
audio file to POST /transcribe via the API.

Usage:
    python scripts/transcribe_folder.py /path/to/videos/
    python scripts/transcribe_folder.py /path/to/videos/ --recursive
    python scripts/transcribe_folder.py /path/to/videos/ --dry-run
"""

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")

API_BASE_URL = os.getenv("ASSISTENTE_API_URL", "http://127.0.0.1:8000")


def _api_request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=f"{API_BASE_URL}{path}",
        data=data,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"API error {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not connect to API at {API_BASE_URL}. "
            "Start it with: uvicorn app.api:app --reload"
        ) from exc


def extract_audio(video_path: Path, ai_data_dir: Path) -> Path | None:
    audio_path = ai_data_dir / (video_path.stem + ".mp3")
    if audio_path.exists():
        return audio_path

    ai_data_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "44100",
                "-ab",
                "128k",
                "-f",
                "mp3",
                str(audio_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return audio_path
    except subprocess.CalledProcessError as exc:
        print(f"  →  FFmpeg error: {exc}")
        return None


def find_videos(folder: Path, recursive: bool) -> list[Path]:
    if recursive:
        files = [p for p in folder.rglob("*") if p.suffix.lower() in VIDEO_EXTENSIONS]
    else:
        files = [p for p in folder.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS]
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(
        description="Extract audio from videos and send each to the transcription API."
    )
    parser.add_argument("folder", type=Path, help="Folder to scan for video files")
    parser.add_argument(
        "--recursive", action="store_true", help="Scan subfolders recursively"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be processed without doing anything",
    )
    args = parser.parse_args()

    folder = args.folder.resolve()
    if not folder.is_dir():
        parser.error(f"Not a directory: {folder}")

    videos = find_videos(folder, args.recursive)
    if not videos:
        print(f"No video files found in {folder}")
        return

    print(f"Found {len(videos)} video(s) in {folder}\n")

    sent = 0
    failed = 0

    for video in videos:
        ai_data_dir = video.parent.parent / "ai_data"
        audio_path = ai_data_dir / (video.stem + ".mp3")

        print(f"  {video.name}")

        if args.dry_run:
            print(f"    [dry-run] extract → {audio_path}")
            print("    [dry-run] transcribe → POST /transcribe")
            continue

        # Step 1: extract audio
        print("    extracting audio...", end="", flush=True)
        audio = extract_audio(video, ai_data_dir)
        if audio is None:
            print("  FAILED (FFmpeg)")
            failed += 1
            continue
        print(f" {audio.name}")

        # Step 2: send to transcription API
        print("    transcribing...", end="", flush=True)
        try:
            result = _api_request("POST", "/transcribe", {"file_path": str(audio)})
            print(f" done  ({result.get('output_file', '')})")
            sent += 1
        except RuntimeError as exc:
            print(f" ERROR: {exc}")
            failed += 1

    print(f"\nDone: {sent} transcribed, {failed} failed.")


if __name__ == "__main__":
    main()
