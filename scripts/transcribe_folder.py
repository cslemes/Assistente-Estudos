"""
Usage:
    python scripts/transcribe_folder.py /path/to/videos/
    python scripts/transcribe_folder.py /path/to/videos/ --recursive
    python scripts/transcribe_folder.py /path/to/videos/ --dry-run

When the API runs inside Docker, set API_DOWNLOADS_BASE so host paths are
translated to container-internal paths before being sent to the server:

    API_DOWNLOADS_BASE=/app/Downloads python scripts/transcribe_folder.py ...
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api_client import api_request

from app.config.settings import VIDEO_EXTENSIONS

# Host-side Downloads root (used for path translation when API runs in Docker)
_DOWNLOADS_BASE = Path(__file__).resolve().parent.parent / "Downloads"
_API_DOWNLOADS_BASE = os.getenv("API_DOWNLOADS_BASE")  # e.g. /app/Downloads


def _path_for_api(local_path: Path) -> str:
    """Return the path the API server should use.

    When API_DOWNLOADS_BASE is set, translates the host absolute path to the
    container-internal path (e.g. /d/.../Downloads/x → /app/Downloads/x).
    """
    if not _API_DOWNLOADS_BASE:
        return str(local_path)
    try:
        rel = local_path.relative_to(_DOWNLOADS_BASE)
        return str(Path(_API_DOWNLOADS_BASE) / rel)
    except ValueError:
        return str(local_path)


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
        files = [
            p
            for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        ]
    else:
        files = [
            p
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        ]
    return sorted(files)


def _has_transcript(ai_data_dir: Path, video_stem: str) -> bool:
    """Return True if a transcript already exists for this video.

    Checks the exact stem first, then any .mp3/.txt pair in ai_data/ — this
    handles the case where the video was renamed by organize_downloads.py after
    the transcript was created (the .txt keeps the old audio stem).
    """
    if (ai_data_dir / f"{video_stem}.txt").exists():
        return True
    if ai_data_dir.is_dir():
        for mp3 in ai_data_dir.glob("*.mp3"):
            if mp3.with_suffix(".txt").exists():
                return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Extract audio from videos and send each to the transcription API."
    )
    parser.add_argument("folder", type=Path, help="Folder to scan for video files")
    parser.add_argument(
        "--recursive", action="store_true", help="Scan subfolders recursively"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List files without processing"
    )
    parser.add_argument(
        "--uploaded-only",
        action="store_true",
        help="Only transcribe videos that have a .uploaded marker (already on YouTube)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-transcribe even if a .txt transcript already exists",
    )
    args = parser.parse_args()

    folder = args.folder.resolve()
    if not folder.is_dir():
        parser.error(f"Not a directory: {folder}")

    videos = find_videos(folder, args.recursive)
    if not videos:
        print(f"No video files found in {folder}")
        return

    if args.uploaded_only:
        videos = [v for v in videos if (v.parent / (v.name + ".uploaded")).exists()]
        if not videos:
            print("No uploaded videos found (no .uploaded markers).")
            return

    print(f"Found {len(videos)} video(s) in {folder}\n")

    sent = 0
    skipped = 0
    failed = 0

    for video in videos:
        ai_data_dir = video.parent.parent / "ai_data"
        print(f"  {video.name}")

        if args.dry_run:
            done = _has_transcript(ai_data_dir, video.stem)
            status = "already done" if done else "will transcribe"
            print(f"    [dry-run] {status}  → {ai_data_dir / (video.stem + '.mp3')}")
            continue

        if not args.force and _has_transcript(ai_data_dir, video.stem):
            print(f"    skipped (transcript exists)")
            skipped += 1
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
            result = api_request("POST", "/transcribe", {"file_path": _path_for_api(audio)})
            print(f" done  ({result.get('output_file', '')})")
            sent += 1
        except RuntimeError as exc:
            msg = str(exc)
            if "404" in msg and not _API_DOWNLOADS_BASE:
                msg += "\n    Hint: set API_DOWNLOADS_BASE=/app/Downloads if the API runs in Docker"
            print(f" ERROR: {msg}")
            failed += 1

    print(f"\nDone: {sent} transcribed, {skipped} skipped (already done), {failed} failed.")


if __name__ == "__main__":
    main()
