"""
Rename video files to a clean format based on folder context.

Pattern: "Curso de Extensão Aula 09 - DL PYTHON 25.1.mp4"  → Aula_09_Autoencoder.mp4
         "video1711686807.mp4" (extra file, no aula number) → Aula_09_Autoencoder_1.mp4

Videos with an aula number in the filename are the "main" video.
Extra videos in the same folder inherit the main video's name with a counter suffix.
The topic is taken from the grandparent folder (parent of the video/ subfolder).

Usage:
    python scripts/rename_videos.py /path/to/folder
    python scripts/rename_videos.py /path/to/folder --recursive
    python scripts/rename_videos.py /path/to/folder --dry-run
"""

import argparse
import re
from pathlib import Path

from app.config.settings import VIDEO_EXTENSIONS
AULA_PATTERN = re.compile(r"aula\s*(\d+)", re.IGNORECASE)


def extract_aula_number(filename: str) -> str | None:
    match = AULA_PATTERN.search(filename)
    return match.group(1).zfill(2) if match else None


def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"[^\w]", "", text)
    return text


def find_videos(folder: Path, recursive: bool) -> list[Path]:
    if recursive:
        return sorted(
            p for p in folder.rglob("*") if p.suffix.lower() in VIDEO_EXTENSIONS
        )
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS)


def plan_renames(videos: list[Path]) -> list[tuple[Path, str]]:
    """
    Returns a list of (original_path, new_name) pairs.
    Groups videos by their parent directory so extras in the same folder
    inherit the main video's name with a counter suffix.
    """
    renames = []

    # Group by parent directory
    by_dir: dict[Path, list[Path]] = {}
    for v in videos:
        by_dir.setdefault(v.parent, []).append(v)

    for parent, group in by_dir.items():
        topic = slugify(parent.parent.name)

        # Split into main (has aula number) and extras
        mains = [(v, extract_aula_number(v.name)) for v in group]
        main_videos = [(v, num) for v, num in mains if num is not None]
        extra_videos = [v for v, num in mains if num is None]

        if not main_videos:
            # No aula number found in any file — skip all
            for v in group:
                print(f"  SKIP  {v.name}  (no aula number found in folder)")
            continue

        # Use the first main video's aula number as the base name
        main_video, aula_num = main_videos[0]
        base_stem = f"Aula_{aula_num}_{topic}"

        # Main video
        renames.append((main_video, f"{base_stem}{main_video.suffix}"))

        # Additional main videos (multiple aula numbers in same folder — rare)
        for v, num in main_videos[1:]:
            renames.append((v, f"Aula_{num}_{topic}{v.suffix}"))

        # Extra videos without aula number
        for counter, v in enumerate(extra_videos, start=1):
            renames.append((v, f"{base_stem}_{counter}{v.suffix}"))

    return renames


def main():
    parser = argparse.ArgumentParser(
        description="Rename videos to Aula_NN_Topic.mp4 based on folder name."
    )
    parser.add_argument("folder", type=Path, help="Folder to scan")
    parser.add_argument("--recursive", action="store_true", help="Scan subfolders")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without renaming"
    )
    args = parser.parse_args()

    folder = args.folder.resolve()
    if not folder.is_dir():
        parser.error(f"Not a directory: {folder}")

    videos = find_videos(folder, args.recursive)
    if not videos:
        print(f"No video files found in {folder}")
        return

    renames = plan_renames(videos)

    renamed = 0
    skipped = 0
    failed = 0

    for video, new_name in renames:
        new_path = video.parent / new_name

        if new_path == video:
            print(f"  OK    {video.name}  (already correctly named)")
            skipped += 1
            continue

        if new_path.exists():
            print(f"  SKIP  {video.name}  → {new_name}  (target already exists)")
            skipped += 1
            continue

        print(
            f"  {'[dry-run] ' if args.dry_run else ''}RENAME  {video.name}  →  {new_name}"
        )

        if not args.dry_run:
            try:
                video.rename(new_path)
                renamed += 1
            except Exception as e:
                print(f"    ERROR: {e}")
                failed += 1

    if not args.dry_run:
        print(f"\nDone: {renamed} renamed, {skipped} skipped, {failed} failed.")


if __name__ == "__main__":
    main()
