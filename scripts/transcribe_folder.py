"""
Usage:
    python scripts/transcribe_folder.py /path/to/videos/
    python scripts/transcribe_folder.py /path/to/videos/ --recursive
    python scripts/transcribe_folder.py /path/to/videos/ --dry-run
"""

import argparse
import subprocess
from pathlib import Path

from api_client import api_request
from app.config.settings import VIDEO_EXTENSIONS


def extract_audio(video_path: Path, ai_data_dir: Path) -> Path | None:
    audio_path = ai_data_dir / (video_path.stem + ".mp3")
    if audio_path.exists():
        return audio_path

    ai_data_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i", str(video_path),
                "-vn", "-ac", "1", "-ar", "44100", "-ab", "128k",
                "-f", "mp3", str(audio_path),
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
        files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
    else:
        files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(
        description="Extract audio from videos and send each to the transcription API."
    )
    parser.add_argument("folder", type=Path, help="Folder to scan for video files")
    parser.add_argument("--recursive", action="store_true", help="Scan subfolders recursively")
    parser.add_argument("--dry-run", action="store_true", help="List files without processing")
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
        print(f"  {video.name}")

        if args.dry_run:
            print(f"    [dry-run] extract → {ai_data_dir / (video.stem + '.mp3')}")
            print("    [dry-run] transcribe → POST /transcribe")
            continue

        print("    extracting audio...", end="", flush=True)
        audio = extract_audio(video, ai_data_dir)
        if audio is None:
            print("  FAILED (FFmpeg)")
            failed += 1
            continue
        print(f" {audio.name}")

        print("    transcribing...", end="", flush=True)
        try:
            result = api_request("POST", "/transcribe", {"file_path": str(audio)})
            print(f" done  ({result.get('output_file', '')})")
            sent += 1
        except RuntimeError as exc:
            print(f" ERROR: {exc}")
            failed += 1

    print(f"\nDone: {sent} transcribed, {failed} failed.")


if __name__ == "__main__":
    main()
